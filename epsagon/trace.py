"""
Trace object holds events and metadata
"""

from __future__ import absolute_import
import sys
import json
import requests
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
        self.metadata = {
            'version': __version__,
            'platform': 'Python {}.{}'.format(
                sys.version_info.major,
                sys.version_info.minor
            )
        }

    def prepare(self):
        """
        Prepares new trace.
        Prints error if token is empty, and empty events list.
        :return: None
        """

        if self.token == '':
            print 'Epsagon Error: Please initialize token, data won\'t be sent.'

        self.events = []

    def initialize(self, app_name, token):
        """
        Initializes trace with user's data.
        User can configure here trace parameters.
        :param app_name: application name
        :param token: user's token
        :return: None
        """

        self.app_name = app_name
        self.token = token

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
        trace.metadata = trace_data.get('metadata', {})
        for event in trace_data['events']:
            trace.events.append(BaseEvent.load_from_dict(event))
        return trace

    def get_events(self):
        """
        get events
        :return: events list
        """

        return self.events

    def add_event(self, event):
        """
        Add event to events list
        :param event: BaseEvent
        :return: None
        """
        event.terminate()
        self.events.append(event)

    def dictify(self):
        """
        Convert trace to dict
        :return: Trace dict
        """

        return {
            'token': self.token,
            'app_name': self.app_name,
            'events': [event.dictify() for event in self.events],
            'exceptions': self.exceptions,
            'metadata': self.metadata,
        }

    def send_traces(self):
        """
        Send trace to collector
        :return: None
        """

        if self.token == '':
            return

        try:
            requests.post(
                TRACE_COLLECTOR_URL,
                data=json.dumps(self.dictify()),
                timeout=SEND_TIMEOUT
            )
        except requests.ReadTimeout as _:
            pass
        except Exception as _:
            pass


tracer = Trace()


def init(token, app_name='default'):
    """
    Initializes trace with user's data.
    User can configure here trace parameters.
    :param app_name: application name
    :param token: user's token
    :return: None
    """

    tracer.initialize(
        token=token,
        app_name=app_name,
    )
