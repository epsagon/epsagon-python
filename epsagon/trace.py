"""
Trace object holds events and metadata
"""

from __future__ import absolute_import, print_function
import sys
import os
import time
import traceback
import warnings
import pprint
import simplejson as json

import requests
import requests.exceptions
from epsagon.event import BaseEvent
from epsagon.common import EpsagonWarning
from .constants import SEND_TIMEOUT, MAX_MESSAGE_SIZE, __version__
from .common import ErrorCode


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
        self.events = []
        self.exceptions = []
        self.custom_logs = []
        self.has_custom_error = False
        self.version = __version__
        self.collector_url = ''
        self.metadata_only = True
        self.use_ssl = False
        self.platform = 'Python {}.{}'.format(
            sys.version_info.major,
            sys.version_info.minor
        )

    def add_exception(self, exception, stack_trace, additional_data=''):
        """
        add an exception to the trace
        :param exception: the exception to add
        :param stack_trace: the traceback at the moment of the event
        :param additional_data: a json serializable object that contains
            additional data regarding the exception
        :return: None
        """

        exception_dict = {
            'type': str(type(exception)),
            'message': str(exception),
            'traceback': stack_trace,
            'time': time.time(),
            'additional_data': additional_data
        }

        self.exceptions.append(exception_dict)

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
        self.custom_logs = []
        self.has_custom_error = False

    def initialize(self, app_name, token, collector_url, metadata_only,
                   use_ssl):
        """
        Initializes trace with user's data.
        User can configure here trace parameters.
        :param app_name: application name
        :param token: user's token
        :param collector_url: the url to send traces to.
        :param metadata_only: whether to send metadata only or not.
        :return: None
        """

        self.app_name = app_name
        self.token = token
        self.collector_url = collector_url
        self.metadata_only = metadata_only
        self.use_ssl = use_ssl

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
        for event in trace_data['events']:
            trace.events.append(BaseEvent.load_from_dict(event))
        return trace

    def add_event(self, event):
        """
        Add event to events list.
        :param event: BaseEvent
        :return: None
        """
        event.terminate()
        self.events.append(event)

    @staticmethod
    def verify_custom_log(message):
        """
        Verifies custom log message is valid, both in size and type.
        :param message: custom message.
        :return: True/False
        """

        try:
            str_message = str(message)
        # pylint: disable=broad-except
        except Exception:
            return False

        if len(str_message) > MAX_MESSAGE_SIZE:
            return False

        return True

    def add_custom_log(self, severity, message):
        """
        Add custom log row. The format is (timestamp, severity, message).
        :param severity: log / error
        :param message: Log message
        :return: True if message added, else False.
        """
        if not Trace.verify_custom_log(message):
            return False
        self.custom_logs.append([time.time(), severity, str(message)])
        return True

    def add_log(self, message):
        """
        Adds log message.
        :param message: Log message
        :return: None
        """
        self.add_custom_log('log', message)

    def add_error(self, message):
        """
        Adds error message and sets error status.
        :param message: Log message
        :return: None
        """
        if self.add_custom_log('error', message):
            self.has_custom_error = True

    def update_runner_with_custom_logs(self):
        """
        Insert custom logs to runner event.
        :return: None
        """
        if not self.custom_logs:
            return

        ind, runner = [
            (ind, ev) for (ind, ev) in enumerate(self.events)
            if ev.origin == 'runner'
        ][0]
        runner.resource['metadata']['Custom Logs'] = self.custom_logs
        if self.has_custom_error and runner.error_code != ErrorCode.EXCEPTION:
            runner.error_code = ErrorCode.ERROR
        self.events[ind] = runner

    def to_dict(self):
        """
        Convert trace to dict.
        :return: Trace dict
        """

        try:
            self.update_runner_with_custom_logs()
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
            'events': [event.to_dict() for event in self.events],
            'exceptions': self.exceptions,
            'version': self.version,
            'platform': self.platform,
        }

    # pylint: disable=W0703
    def send_traces(self):
        """
        Send trace to collector.
        :return: None
        """
        if self.token == '':
            return
        try:
            requests.post(
                self.collector_url,
                data=json.dumps(self.to_dict()),
                timeout=SEND_TIMEOUT
            )
            if os.environ.get('EPSAGON_DEBUG') == 'TRUE':
                print("Sending traces:")
                pprint.pprint(self.to_dict())
        except requests.exceptions.ReadTimeout as _:
            # In future, send basic data
            pass
        except Exception as _:
            pass


# pylint: disable=C0103
tracer = Trace()
