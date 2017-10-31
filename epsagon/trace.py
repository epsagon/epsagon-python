"""

"""

from __future__ import absolute_import
import time
from uuid import uuid4
import ujson
import requests
from .common import ErrorCode
from .constants import TRACE_COLLECTOR_URL


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
        self.trigger = None
        self.runner = None
        self.operations = []

    def initialize(self, app_name, token):
        self.trace_id = str(uuid4())
        self.app_name = app_name
        self.token = token
        self.start_timestamp = time.time()
        self.end_timestamp = 0
        self.error_code = ErrorCode.OK
        self.trigger = None
        self.runner = None
        self.operations = []

    @staticmethod
    def load_from_dict(trace_data):
        trace = Trace()
        trace.trace_id = trace_data['id']
        trace.app_name = trace_data['app_name']
        trace.token = trace_data['token']
        trace.start_timestamp = trace_data['start_timestamp']
        trace.end_timestamp = trace_data['end_timestamp']
        trace.error_code = trace_data['error_code']
        return trace

    def get_events(self):
        if self.trigger is None:
            events = [self.runner] + self.operations
        else:
            events = [self.trigger, self.runner] + self.operations

        return events

    def dictify(self):
        return {
            'id': self.trace_id,
            'token': self.token,
            'app_name': self.app_name,
            'start_timestamp': self.start_timestamp,
            'end_timestamp': self.end_timestamp,
            'error_code': self.error_code,
            'trigger': self.trigger.dictify(),
            'runner': self.runner.dictify(),
            'operations': [operation.dictify() for operation in self.operations]
        }

    def send_traces(self):
        if self.end_timestamp == 0:
            self.end_timestamp = time.time()

        try:
            requests.post(TRACE_COLLECTOR_URL, data=ujson.dumps(self.dictify()))
        except Exception as exception:
            # TODO: Think of what needs to be done if there is an error in send
            pass


tracer = Trace()
