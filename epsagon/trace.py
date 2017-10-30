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
            pass


tracer = Trace()
