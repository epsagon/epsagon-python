"""

"""

from __future__ import absolute_import
import time
import sys
import requests
import json

from uuid import uuid4
from epsagon.event import BaseEvent
from .common import ErrorCode
from .constants import TRACE_COLLECTOR_URL, __version__


class Trace(object):
    """
    Represents runtime trace
    """

    def __init__(self):
        self.trace_id = ''
        self.app_name = ''
        self.token = ''
        self.start_timestamp = 0
        self.end_timestamp = 0
        self.error_code = ErrorCode.OK
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
        if self.token == '':
            print 'Epsagon Error: Please initialize token, data won\'t be sent.'
        self.trace_id = str(uuid4())
        self.start_timestamp = time.time()
        self.end_timestamp = 0
        self.error_code = ErrorCode.OK
        self.events = []

    def initialize(self, app_name, token):
        self.app_name = app_name
        self.token = token

    @staticmethod
    def load_from_dict(trace_data):
        trace = Trace()
        trace.trace_id = trace_data['id']
        trace.app_name = trace_data['app_name']
        trace.token = trace_data['token']
        trace.start_timestamp = trace_data['start_timestamp']
        trace.end_timestamp = trace_data['end_timestamp']
        trace.error_code = trace_data['error_code']
        trace.metadata = trace_data.get('metadata', {})
        for event in trace_data['events']:
            trace.events.append(BaseEvent.load_from_dict(event))
        return trace

    def get_events(self):
        return self.events

    def add_event(self, event):
        event.terminate()
        self.events.append(event)

    def set_error(self):
        self.error_code = ErrorCode.ERROR

    def dictify(self):
        return {
            'id': self.trace_id,
            'token': self.token,
            'app_name': self.app_name,
            'start_timestamp': self.start_timestamp,
            'end_timestamp': self.end_timestamp,
            'error_code': self.error_code,
            'metadata': self.metadata,
            'events': [event.dictify() for event in self.events],
            'exceptions': self.exceptions,
        }

    def send_traces(self):

        if self.token == '':
            return

        if self.end_timestamp == 0:
            self.end_timestamp = time.time()

        try:
            requests.post(TRACE_COLLECTOR_URL, data=json.dumps(self.dictify()))
        except Exception as exception:
            print 'Epsagon Error: Could not send traces {}'.format(
                exception.message)


tracer = Trace()
