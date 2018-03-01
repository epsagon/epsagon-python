"""
Trace object holds events and metadata
"""

from __future__ import absolute_import
import sys
import time
import warnings
import requests
import simplejson as json
from epsagon.event import BaseEvent
from .constants import TRACE_COLLECTOR_URL, SEND_TIMEOUT, __version__


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
        self.version = __version__
        self.collector_url = TRACE_COLLECTOR_URL
        self.metadata_only = True
        self.platform = 'Python {}.{}'.format(
            sys.version_info.major,
            sys.version_info.minor
        )

    def add_exception(self, exception, stack_trace):
        """
        add an exception to the trace
        :param exception: the exception to add
        :param stack_trace: the traceback at the moment of the event
        :return: None
        """

        exception_dict = {
            'type': str(type(exception)),
            'message': str(exception),
            'traceback': stack_trace,
            'time': time.time()
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
                'Epsagon Error: Please initialize token, data won\'t be sent.')

        self.events = []
        self.exceptions = []

    def initialize(self, app_name, token, collector_url, metadata_only):
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

    def to_dict(self):
        """
        Convert trace to dict.
        :return: Trace dict
        """

        return {
            'token': self.token,
            'app_name': self.app_name,
            'events': [event.to_dict() for event in self.events],
            'exceptions': self.exceptions,
            'version': self.version,
            'platform': self.platform,
        }

    # pylint: disable=W0702
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
        # except requests.ReadTimeout as _:
        #     # In future, send basic data
        #     pass
        except:  # noqa: E722
            pass


tracer = Trace()


def init(token,
         app_name='default',
         collector_url=TRACE_COLLECTOR_URL,
         metadata_only=True
         ):
    """
    Initializes trace with user's data.
    User can configure here trace parameters.
    :param token: user's token
    :param app_name: application name
    :param collector_url: the url of the collector.
    :param metadata_only: whether to send only the metadata, or also the data.
    :return: None
    """

    tracer.initialize(
        token=token,
        app_name=app_name,
        collector_url=collector_url,
        metadata_only=metadata_only
    )
