"""
Trace object holds events and metadata
"""
# pylint: disable=too-many-lines

from __future__ import absolute_import, print_function
import os
import sys
import time
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
from epsagon.trace_encoder import TraceEncoder
from epsagon.trace_transports import NoneTransport, HTTPTransport, LogTransport
from .constants import (
    TIMEOUT_GRACE_TIME_MS,
    MAX_LABEL_SIZE,
    is_strong_key,
    __version__
)

MAX_EVENTS_PER_TYPE = 20
MAX_TRACE_SIZE_BYTES = 64 * (2 ** 10)
DEFAULT_MAX_TRACE_SIZE_BYTES = 64 * (2 ** 10)


def get_thread_id():
    """
    Return current thread id
    :return: thread id
    """
    return threading.currentThread().ident


def create_transport(collector_url, token):
    if (os.getenv('EPSAGON_LOG_TRANSPORT') or '').upper() == 'TRUE':
        return LogTransport()
    return HTTPTransport(collector_url, token)


# pylint: disable=R0904
class TraceFactory(object):
    """
    A trace factory.
    """

    LOCK = threading.Lock()

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
        self.local_thread_to_unique_id = {}
        self.transport = NoneTransport()
        self.split_on_send = False
        self.disabled = False

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
            keys_to_ignore,
            transport,
            split_on_send,
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
        :param split_on_send: Split trace into multiple traces in case it's size
         exceeds the maximum size.
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
        self.transport = transport
        self.split_on_send = split_on_send

        self.update_tracers()

    def update_tracers(self):
        """
        Update tracers to have latest parameters in case of re-initialization
        of the factory.
        """
        tracers_to_update = (
            [self.singleton_trace, ] if self.singleton_trace else
            self.traces
        )

        for tracer in tracers_to_update:
            tracer.app_name = self.app_name
            tracer.token = self.token
            tracer.collector_url = self.collector_url
            tracer.metadata_only = self.metadata_only
            tracer.disable_timeout_send = self.disable_timeout_send
            tracer.debug = self.debug
            tracer.send_trace_only_on_error = self.send_trace_only_on_error
            tracer.url_patterns_to_ignore = self.url_patterns_to_ignore
            tracer.keys_to_ignore = self.keys_to_ignore
            tracer.transport = self.transport
            tracer.split_on_send = self.split_on_send

    def switch_to_multiple_traces(self):
        """
        Set the use_single_trace flag to False.
        :return: None
        """
        self.use_single_trace = False

    def _create_new_trace(self, unique_id=None):
        """
        Creating new trace instance
        :param unique_id: trace unique id
        :return: new trace
        """
        return Trace(
            self.app_name,
            self.token,
            self.collector_url,
            self.metadata_only,
            self.disable_timeout_send,
            self.debug,
            self.send_trace_only_on_error,
            self.url_patterns_to_ignore,
            self.keys_to_ignore,
            unique_id,
            self.split_on_send,
        )

    def get_or_create_trace(self, unique_id=None):
        """
        Gets or create a trace - thread-safe
        :param unique_id: unique id
        :return: trace
        """
        with TraceFactory.LOCK:
            return self._get_or_create_trace(unique_id)

    def _get_or_create_trace(self, unique_id=None):
        """
        Get or create trace based on the use_single_trace flag.
        if use_single_trace is set to False, each thread will have
        it's own trace.
        :return: The trace.
        """
        unique_id = self.get_thread_local_unique_id(unique_id)
        if unique_id:
            trace = (
                self.singleton_trace
                if self.singleton_trace and not self.traces
                else self.traces.get(
                    unique_id, None
                )
            )
            if not trace:
                trace = self._create_new_trace(unique_id)
            # Making sure singleton trace contains the latest trace
            trace.unique_id = unique_id
            self.singleton_trace = trace
            self.traces[unique_id] = trace
            return trace

        if self.use_single_trace:
            if self.singleton_trace is None:
                self.singleton_trace = self._create_new_trace()
            return self.singleton_trace

        # If multiple threads are used, then create a new trace for each thread
        thread_id = self.get_trace_identifier()
        if thread_id not in self.traces:
            new_trace = self._create_new_trace()
            self.traces[thread_id] = new_trace
        return self.traces[thread_id]

    @property
    def active_trace(self):
        """
        Return the active trace
        :return: None
        """
        local_unique_id = self.get_thread_local_unique_id()
        return self.traces.get(local_unique_id, self.singleton_trace)

    def switch_active_trace(self, unique_id):
        """
        Sets the active trace by unique id
        :return: unique id
        """
        with self.LOCK:
            trace = self.traces.get(unique_id, None)
            if trace:
                self.singleton_trace = trace
            return trace

    def pop_trace(self, trace=None):
        """
        Sets the active trace by unique id
        :return: unique id
        """
        with self.LOCK:
            if self.traces:
                trace = self.traces.pop(self.get_trace_identifier(trace), None)
                if not self.traces:
                    self.singleton_trace = None
                return trace
            if not trace:
                trace = self.singleton_trace
                self.singleton_trace = None
                return trace
            return None

    def get_thread_local_unique_id(self, unique_id=None):
        """
        Get thread local unique id
        :param unique_id: input unique id
        :return: active id if there's an active unique id or given one
        """
        return self.local_thread_to_unique_id.get(
            get_thread_id(), unique_id
        )

    def set_thread_local_unique_id(self, unique_id=None):
        """
        Set thread local unique id
        :param unique_id: input unique id
        :return: the active unique id
        """
        unique_id = (
            unique_id if unique_id else (
                self.singleton_trace.unique_id if self.singleton_trace else None
            )
        )
        self.local_thread_to_unique_id[get_thread_id()] = unique_id
        return unique_id

    def unset_thread_local_unique_id(self):
        """
        Unset thread local unique id
        :return: None
        """
        self.local_thread_to_unique_id.pop(get_thread_id(), None)

    def get_trace_identifier(self, trace=None):
        """
        Return the trace identifier
        :return: trace identifier
        """
        if not trace:
            trace = self.singleton_trace

        return (
            get_thread_id()
            if not trace or not trace.unique_id
            else trace.unique_id
        )

    def get_trace(self):
        """
        Get the relevant trace (may be thread-based or a singleton trace)
        :return:
        """
        return self.get_or_create_trace()

    def add_event(self, event):
        """
        Add  event to the relevant trace.
        :param event: The event to add.
        :return: None
        """
        trace = self.get_trace()
        if trace:
            trace.add_event(event)

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

    def send_traces(self, trace=None):
        """
        Send the traces for the current thread.
        :return: None
        """
        if self.disabled:
            print('EPSAGON: Trace not sent (disabled).')
            return

        trace = trace if trace else self.get_trace()

        if trace:
            trace.send_traces()
            self.pop_trace(trace)

    def prepare(self):
        """
        Prepare the relevant trace.
        :return: None
        """
        trace = self.get_trace()
        if trace:
            trace.prepare()

    def enable(self):
        """
        Enables Epsagon
        :return: None
        """
        self.disabled = False

    def disable(self):
        """
        Disables Epsagon
        :return: None
        """
        self.disabled = True


# pylint: disable=too-many-public-methods
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
            keys_to_ignore=None,
            unique_id=None,
            split_on_send=False,
            transport=NoneTransport(),
    ):
        """
        initialize.
        """
        self.app_name = app_name
        self.unique_id = unique_id
        self.token = token
        self.events = []
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
        self.transport = transport
        self.split_on_send = split_on_send

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

        self.events = []
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
        trace.events = []
        for event in trace_data['events']:
            trace.add_event(BaseEvent.load_from_dict(event))
        return trace

    def set_runner(self, runner):
        """
        Sets the runner of the current tracer
        :param runner: Runner to set
        """
        self.add_event(runner, should_terminate=False)
        self.runner = runner

    def clear_events(self):
        """
        Clears the events list
        :return: None
        """
        self.events = []

    def add_event(self, event, should_terminate=True):
        """
        Add event to events list.
        :param event: BaseEvent
        :param should_terminate: If True, `event.terminate()` is called
        :return: None
        """
        if should_terminate:
            event.terminate()
        self.events.append(event)

    def verify_custom_label(self, key, value):
        """
        Verifies custom label is valid, both in size and type.
        :param key: Key for the label data (string)
        :param value: Value for the label data (string)
        :return: True/False
        """
        if not isinstance(key, str) or not isinstance(value, str):
            print('EPSAGON: epsagon.label() only supports '
                  'label keys and values of type string.')
            print('Received {key}:{value}'.format(key=key, value=value))
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
            if getattr(exception, '__traceback__', None):
                traceback_data = ''.join(traceback.format_exception(
                    type(exception),
                    exception,
                    getattr(exception, '__traceback__'),
                ))
            else:
                traceback_data = ''.join(
                    traceback.format_list(traceback.extract_stack())
                )
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
            'events': [event.to_dict() for event in self.events],
            'exceptions': self.exceptions,
            'version': self.version,
            'platform': self.platform,
        }

    @staticmethod
    def trim_metadata(metadata):
        """
        Trimming metadata
        :param metadata: metadata
        :return:
        """
        for key in list(metadata.keys()):
            if not is_strong_key(key):
                metadata.pop(key)

    @staticmethod
    def events_sorter(event):
        """
        Events sort function
        :param event: event
        :return: sorting result
        """
        return 1 if event.origin in ['runner', 'trigger'] else 0

    @property
    def _max_trace_size(self):
        """
        Retreive the max trace size
        """
        max_trace_size = os.getenv('EPSAGON_MAX_TRACE_SIZE')
        if max_trace_size:
            try:
                return int(max_trace_size)
            except ValueError:
                print('Invalid max Epsagon trace size given')

        return DEFAULT_MAX_TRACE_SIZE_BYTES

    @property
    def length(self):
        json_trace = json.dumps(
            self.to_dict(),
            cls=TraceEncoder,
            encoding='latin1'
        )
        return len(json_trace)

    def _strip(self, trace_length):
        """
        Strips a given trace from all operations
        """
        for event in sorted(self.events, key=Trace.events_sorter):
            event_metadata_length = (
                len(json.dumps(
                    event.resource.get('metadata', {}),
                    cls=TraceEncoder,
                    encoding='latin1',
                ))
            )
            Trace.trim_metadata(event.resource['metadata'])
            trace_length -= event_metadata_length
            if trace_length < self._max_trace_size:
                break

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

    def send_traces(self):
        """
        If trace size exceeds the maximum size, and split flag is on
        then split the trace into multiple traces.
        :return: None
        """
        if self.split_on_send and self.length > self._max_trace_size:
            self._send_trace_split()
        else:
            self._send_traces()

    def _send_trace_split(self):
        """
        Split trace into multiple traces and send them one after the other.
        This is done by manipulating the trace object while keeping the same
        runner.
        :param trace: the trace to send.
        """
        # Get only events (without runner)
        all_events = self.events[:]
        if self.runner:
            all_events.remove(self.runner)

        self.runner.resource['metadata']['fragment_seq'] = 1
        self.clear_events()
        self.add_event(self.runner)
        for event in all_events:
            self.add_event(event)
            if self.length > self._max_trace_size:
                self.events.pop()
                self._send_traces()
                self.runner.resource['metadata']['fragment_seq'] += 1
                self.trace_sent = False
                self.clear_events()
                self.add_event(self.runner)
                self.add_event(event)

        # If there are events to send (except for runner)
        if len(self.events) > 1:
            self._send_traces()

    # pylint: disable=W0703
    def _send_traces(self):
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

        self.transport = (
            self.transport
            if not isinstance(self.transport, NoneTransport)
            else create_transport(self.collector_url, self.token)
        )

        # Remove ignored keys.
        for event in self.events:
            self.remove_ignored_keys(event.resource['metadata'])

        try:
            if self.runner:
                self.runner.terminate()

            trace = json.dumps(
                self.to_dict(),
                cls=TraceEncoder,
                encoding='latin1'
            )

            trace_length = len(trace)
            if trace_length > self._max_trace_size:
                # Trace too big.
                self._strip(trace_length)
                self.runner.resource['metadata']['is_trimmed'] = True

                trace = json.dumps(
                    self.to_dict(),
                    cls=TraceEncoder,
                    encoding='latin1'
                )

            self.transport.send(self)
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


# pylint: disable=C0103
trace_factory = TraceFactory()
