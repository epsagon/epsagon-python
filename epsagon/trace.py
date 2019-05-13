"""
Trace object holds events and metadata
"""

from __future__ import absolute_import, print_function
import sys
import time
from datetime import date, datetime
import itertools
import traceback
import warnings
import signal
import pprint
import simplejson as json

import requests
import requests.exceptions
from epsagon.event import BaseEvent
from epsagon.common import EpsagonWarning
from .constants import (
    TIMEOUT_GRACE_TIME_MS,
    SEND_TIMEOUT,
    MAX_LABEL_SIZE,
    __version__
)

MAX_EVENTS_PER_TYPE = 20
MAX_TRACE_SIZE_BYTES = 64 * (2 ** 10)
SESSION = requests.Session()


class TraceEncoder(json.JSONEncoder):
    """
    An encoder for the trace json
    """
    def default(self, o):  # pylint: disable=method-hidden
        if isinstance(o, set):
            return list(o)
        if isinstance(o, (datetime, date)):
            return o.isoformat()

        output = repr(o)
        try:
            output = json.JSONEncoder.default(self, o)
        except TypeError:
            pass
        return output


class Trace(object):
    """
    Represents runtime trace
    """

    def __init__(self):
        """
        initialize.
        """

        self.app_name = ''
        self.token = ''
        self.events_map = {}
        self.exceptions = []
        self.custom_labels = {}
        self.custom_labels_size = 0
        self.has_custom_error = False
        self.version = __version__
        self.collector_url = ''
        self.metadata_only = True
        self.disable_timeout_send = False
        self.debug = False
        self.platform = 'Python {}.{}'.format(
            sys.version_info.major,
            sys.version_info.minor
        )
        self.runner = None
        self.trace_sent = False

    # pylint: disable=unused-argument, unused-variable
    def timeout_handler(self, signum, frame):
        """
        Send a trace in case of timeout.
        Invoked by a pre-set alarm.
        """
        try:
            if self.debug:
                print('Epsagon timeout handler called. Stack trace:')
                traceback.print_stack(limit=100)

            self.runner.set_timeout()
            self.send_traces()

            # pylint: disable=W0703
        except Exception:
            pass

    @staticmethod
    def reset_timeout_handler():
        """
        Cancel an already set alarm.
        """
        signal.alarm(0)

    def set_timeout_handler(self, context):
        """
        Sets a timeout handler for the current tracer.
        :param context: context, as received by Lambda.
        """
        try:
            if not hasattr(context, 'get_remaining_time_in_millis'):
                return

            original_timeout = context.get_remaining_time_in_millis()
            if original_timeout <= TIMEOUT_GRACE_TIME_MS:
                return

            modified_timeout = (
                original_timeout - TIMEOUT_GRACE_TIME_MS) / 1000.0

            signal.setitimer(signal.ITIMER_REAL, modified_timeout)
            original_handler = signal.signal(
                signal.SIGALRM,
                self.timeout_handler
            )

            # pylint: disable=comparison-with-callable
            if (
                original_handler and
                original_handler != self.timeout_handler
            ):
                warnings.warn(
                    'Epsagon Warning: Overriding existing '
                    'SIGALRM handler {!r}'.format(original_handler)
                )

        # pylint: disable=W0703
        except Exception:
            pass

    def add_exception(self, exception, stack_trace, additional_data=''):
        """
        add an exception to the trace
        :param exception: the exception to add
        :param stack_trace: the traceback at the moment of the event
        :param additional_data: a json serializable object that contains
            additional data regarding the exception
        :return: None
        """

        try:
            exception_dict = {
                'type': str(type(exception)),
                'message': str(exception),
                'traceback': stack_trace,
                'time': time.time(),
                'additional_data': additional_data
            }

            self.exceptions.append(exception_dict)
        # Making sure that tracing inner exception won't crash
        # pylint: disable=W0703
        except Exception:
            pass

    def prepare(self):
        """
        Prepares new trace.
        Prints error if token is empty, and empty events list.
        :return: None
        """

        if self.token == '':
            warnings.warn(
                'Epsagon Error: Please initialize token, data won\'t be sent.',
                EpsagonWarning
            )

        self.events_map = {}
        self.exceptions = []
        self.custom_labels = {}
        self.custom_labels_size = 0
        self.has_custom_error = False
        self.runner = None
        self.trace_sent = False

    def initialize(
        self,
        app_name,
        token,
        collector_url,
        metadata_only,
        disable_timeout_send,
        debug
    ):
        """
        Initializes trace with user's data.
        User can configure here trace parameters.
        :param app_name: application name
        :param token: user's token
        :param collector_url: the url to send traces to.
        :param metadata_only: whether to send metadata only or not.
        :param disable_timeout_send: whether to disable traces send on timeout
         (when enabled, is done using a signal handler).
        :param debug: debug flag
        :return: None
        """

        self.app_name = app_name
        self.token = token
        self.collector_url = collector_url
        self.metadata_only = metadata_only
        self.disable_timeout_send = disable_timeout_send
        self.debug = debug

    @staticmethod
    def load_from_dict(trace_data):
        """
        Load new trace object from dict.
        :param trace_data: dict data of trace
        :return: Trace
        """

        trace = Trace()
        trace.app_name = trace_data['app_name']
        trace.token = trace_data['token']
        trace.version = trace_data['version']
        trace.platform = trace_data['platform']
        trace.exceptions = trace_data.get('exceptions', [])
        trace.events_map = {}
        for event in trace_data['events']:
            trace.add_event(BaseEvent.load_from_dict(event))
        return trace

    def set_runner(self, runner):
        """
        Sets the runner of the current tracer
        :param runner: Runner to set
        """
        self.add_event(runner)
        self.runner = runner

    def clear_events(self):
        """
        Clears the events list
        :return: None
        """
        self.events_map = {}

    def add_event(self, event):
        """
        Add event to events list.
        :param event: BaseEvent
        :return: None
        """
        event.terminate()
        events = self.events_map.setdefault(event.identifier(), [])
        if len(events) < MAX_EVENTS_PER_TYPE:
            events.append(event)

    def verify_custom_label(self, key, value):
        """
        Verifies custom label is valid, both in size and type.
        :param key: Key for the label data (string)
        :param value: Value for the label data (string)
        :return: True/False
        """
        if not isinstance(key, str) or not isinstance(value, str):
            return False

        if len(key) + len(value) > MAX_LABEL_SIZE:
            return False

        if (
            len(key) +
            len(value) +
            self.custom_labels_size > MAX_LABEL_SIZE
        ):
            return False

        self.custom_labels_size += len(key) + len(value)

        return True

    def events(self):
        """
        Returns events iterator
        :return: events iterator
        """
        return itertools.chain(
            *self.events_map.values()
        )

    def add_label(self, key, value):
        """
        Adds a custom label given by the user to the runner
        of the current trace
        :param key: Key for the label data (string)
        :param value: Value for the label data (string)
        """
        # Convert numbers to string.
        if isinstance(value, (int, float)):
            value = str(value)

        if not self.verify_custom_label(key, value):
            return
        self.custom_labels[key] = value

    def set_error(self, exception, traceback_data=None):
        """
        Sets the error value of the runner
        :param exception: Exception object to set.
        :param traceback_data: traceback string
        """
        if not traceback_data:
            traceback_data = ''.join(traceback.extract_stack().format())
        self.runner.set_exception(exception, traceback_data)

    def update_runner_with_labels(self):
        """
        Adds the custom labels to the runner of the trace
        """
        if not self.custom_labels:
            return

        self.runner.resource['metadata']['labels'] = json.dumps(
            self.custom_labels
        )

    def to_dict(self):
        """
        Convert trace to dict.
        :return: Trace dict
        """
        try:
            self.update_runner_with_labels()
        # pylint: disable=W0703
        except Exception as exception:
            # Ignore custom logs in case of error.
            tracer.add_exception(
                exception,
                traceback.format_exc()
            )

        return {
            'token': self.token,
            'app_name': self.app_name,
            'events': [event.to_dict() for event in self.events()],
            'exceptions': self.exceptions,
            'version': self.version,
            'platform': self.platform,
        }

    def _strip(self):
        """
        Strips a given trace from all operations
        """
        for event in self.events():
            if event.origin == 'runner' or event.origin == 'trigger':
                continue

            del self.events_map[event.identifier()]

    # pylint: disable=W0703
    def send_traces(self):
        """
        Send trace to collector.
        :return: None
        """
        if self.token == '' or self.trace_sent:
            return
        trace = ''
        try:
            if self.runner:
                self.runner.terminate()

            trace = json.dumps(
                self.to_dict(),
                cls=TraceEncoder,
                encoding='latin1'
            )

            if len(trace) > MAX_TRACE_SIZE_BYTES:
                # Trace too big.
                self._strip()
                self.runner.resource['metadata']['is_trimmed'] = True

                trace = json.dumps(
                    self.to_dict(),
                    cls=TraceEncoder,
                    encoding='latin1'
                )

            SESSION.post(
                self.collector_url,
                data=trace,
                timeout=SEND_TIMEOUT,
                headers={'Authorization': 'Bearer {}'.format(self.token)}
            )

            self.trace_sent = True

            if self.debug:
                print('Trace sent (size: {})'.format(
                    len(trace)
                ))
                pprint.pprint(self.to_dict())
        except requests.exceptions.ReadTimeout:
            print('Failed to send trace (size: {}) (timeout)'.format(
                len(trace)
            ))
        except Exception as exception:
            print('Failed to send trace (size: {}): {}'.format(
                len(trace),
                exception
            ))
            if self.debug:
                pprint.pprint(self.to_dict())


# pylint: disable=C0103
tracer = Trace()
