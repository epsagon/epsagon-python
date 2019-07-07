"""
Trace object holds events and metadata
"""
# pylint: disable=too-many-lines

from __future__ import absolute_import, print_function
import sys
import time
from datetime import date, datetime
import itertools
import traceback
import warnings
import signal
import pprint
import threading
import simplejson as json

import requests
import requests.exceptions
from epsagon.event import BaseEvent
from epsagon.common import EpsagonWarning, ErrorCode
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


class TraceFactory(object):
    """
    A trace factory.
    """

    def __init__(self):
        """
        Initialize.
        """
        self.traces = {}
        self.app_name = ''
        self.token = ''
        self.collector_url = ''
        self.metadata_only = True
        self.disable_timeout_send = False
        self.debug = False
        self.send_trace_only_on_error = False
        self.url_patterns_to_ignore = None
        self.keys_to_ignore = None
        self.use_single_trace = True
        self.singleton_trace = None

    def initialize(
            self,
            app_name,
            token,
            collector_url,
            metadata_only,
            disable_timeout_send,
            debug,
            send_trace_only_on_error,
            url_patterns_to_ignore,
            keys_to_ignore
    ):
        """
        Initializes The factory with user's data.
        User can configure here trace parameters.
        :param app_name: application name
        :param token: user's token
        :param collector_url: the url to send traces to.
        :param metadata_only: whether to send metadata only or not.
        :param disable_timeout_send: whether to disable traces send on timeout
         (when enabled, is done using a signal handler).
        :param debug: debug flag.
        :param send_trace_only_on_error: Whether to send trace only when
         there is error or not.
        :param url_patterns_to_ignore: URL patterns to ignore in HTTP data
         collection.
        :param keys_to_ignore: List of keys to ignore while extracting metadata.
        :return: None
        """

        self.app_name = app_name
        self.token = token
        self.collector_url = collector_url
        self.metadata_only = metadata_only
        self.disable_timeout_send = disable_timeout_send
        self.debug = debug
        self.send_trace_only_on_error = send_trace_only_on_error
        self.url_patterns_to_ignore = (
            set(url_patterns_to_ignore) if url_patterns_to_ignore else set()
        )
        self.keys_to_ignore = [] if keys_to_ignore is None else keys_to_ignore

    def switch_to_multiple_traces(self):
        """
        Set the use_single_trace flag to False.
        :return: None
        """
        self.use_single_trace = False

    def get_or_create_trace(self):
        """
        Get or create trace based on the use_single_trace flag.
        if use_single_trace is set to False, each thread will have
        it's own trace.
        :return: The trace.
        """

        if self.use_single_trace:
            if self.singleton_trace is None:
                self.singleton_trace = Trace(
                    self.app_name,
                    self.token,
                    self.collector_url,
                    self.metadata_only,
                    self.disable_timeout_send,
                    self.debug,
                    self.send_trace_only_on_error,
                    self.url_patterns_to_ignore,
                    self.keys_to_ignore
                )
            return self.singleton_trace

        # If multiple threads are used, then create a new trace for each thread
        thread_id = threading.currentThread().ident
        if thread_id not in self.traces:
            new_trace = Trace(
                self.app_name,
                self.token,
                self.collector_url,
                self.metadata_only,
                self.disable_timeout_send,
                self.debug,
                self.send_trace_only_on_error,
                self.url_patterns_to_ignore,
                self.keys_to_ignore

            )
            self.traces[thread_id] = new_trace
        return self.traces[thread_id]

    def get_trace(self):
        """
        Get the relevant trace (may be thread-based or a singleton trace)
        :return:
        """
        if self.use_single_trace:
            return self.singleton_trace

        return self.traces.get(threading.currentThread().ident)

    def remove_current_trace(self):
        """
        Remove the thread's trace only if use_single_trace is set to False.
        """
        if not self.use_single_trace:
            self.traces.pop(threading.currentThread().ident, None)

    def add_event(self, event):
        """
        Add  event to the relevant trace.
        :param event: The event to add.
        :return: None
        """
        if self.get_trace():
            self.get_trace().add_event(event)

    def set_runner(self, event):
        """
        Add a runner event to the relevant trace.
        :param event: The event to add.
        :return: None
        """
        if self.get_trace():
            self.get_trace().set_runner(event)

    def add_exception(self, exception, stack_trace, additional_data=''):
        """
        add an exception to the relevant trace.
        :param exception: the exception to add
        :param stack_trace: the traceback at the moment of the event
        :param additional_data: a json serializable object that contains
            additional data regarding the exception
        :return: None
        """
        if self.get_trace():
            self.get_trace().add_exception(
                exception,
                stack_trace,
                additional_data
            )

    def add_label(self, key, value):
        """
        Add label to the current thread's trace.
        :param key:
        :param value:
        """
        if self.get_trace():
            self.get_trace().add_label(key, value)

    def set_error(self, exception, traceback_data=None):
        """
        Set an error for the current thread's trace.
        :param exception: The exception
        :param traceback_data: The traceback data.
        """
        if self.get_trace():
            self.get_trace().set_error(exception, traceback_data)

    def send_traces(self):
        """
        Send the traces for the current thread.
        :return: None
        """
        if self.get_trace():
            self.get_trace().send_traces()

    def prepare(self):
        """
        Prepare the relevant trace.
        :return: None
        """
        if self.get_trace():
            self.get_trace().prepare()


class Trace(object):
    """
    Represents runtime trace
    """

    def __init__(
            self,
            app_name='',
            token='',
            collector_url='',
            metadata_only=True,
            disable_timeout_send=False,
            debug=False,
            send_trace_only_on_error=False,
            url_patterns_to_ignore=None,
            keys_to_ignore=None

    ):
        """
        initialize.
        """

        self.app_name = app_name
        self.token = token
        self.events_map = {}
        self.exceptions = []
        self.custom_labels = {}
        self.custom_labels_size = 0
        self.has_custom_error = False
        self.version = __version__
        self.collector_url = collector_url
        self.metadata_only = metadata_only
        self.disable_timeout_send = disable_timeout_send
        self.debug = debug
        self.send_trace_only_on_error = send_trace_only_on_error
        self.url_patterns_to_ignore = url_patterns_to_ignore
        if keys_to_ignore:
            self.keys_to_ignore = [self._strip_key(x) for x in keys_to_ignore]
        else:
            self.keys_to_ignore = []
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
        signal.signal(signal.SIGALRM, signal.SIG_DFL)

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
        if not self.runner:
            return

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
            self.add_exception(
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

            self.events_map.pop(event.identifier(), None)

    @staticmethod
    def _strip_key(key):
        """
        Strip a given key from spaces, dashes, and underscores.
        :param key: The key to strip.
        :return: Stripped key.
        """
        return key.lower().replace('-', '').replace('_', '').replace(' ', '')

    def remove_ignored_keys(self, input_dict):
        """
        Remove ignored keys recursively.
        :param input_dict: Input dict to remove ignored keys from.
        :return: None
        """
        if self.keys_to_ignore:
            # Python 2 returns a list, while Python3 returns an iterator.
            for key, value in list(input_dict.items()):
                if self._strip_key(key) in self.keys_to_ignore:
                    input_dict.pop(key)
                else:
                    if isinstance(value, dict):
                        self.remove_ignored_keys(value)

    # pylint: disable=W0703
    def send_traces(self):
        """
        Send trace to collector.
        :return: None
        """
        if self.token == '' or self.trace_sent:
            return
        if (
                self.send_trace_only_on_error and
                self.runner and
                self.runner.error_code == ErrorCode.OK
        ):
            return
        trace = ''

        # Remove ignored keys.
        for event in self.events():
            self.remove_ignored_keys(event.resource['metadata'])

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
        except requests.exceptions.ReadTimeout:
            print('Failed to send trace (size: {}) (timeout)'.format(
                len(trace)
            ))
        except Exception as exception:
            print('Failed to send trace (size: {}): {}'.format(
                len(trace),
                exception
            ))
        finally:
            if self.debug:
                pprint.pprint(self.to_dict())
            trace_factory.remove_current_trace()


# pylint: disable=C0103
trace_factory = TraceFactory()
