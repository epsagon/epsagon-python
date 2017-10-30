"""

"""

from __future__ import absolute_import
import time
from .common import ErrorCode
from .trace import tracer


class BaseEvent(object):
    """
    Represents base trace's event
    """

    EVENT_MODULE = 'base'
    EVENT_TYPE = 'generic'

    def __init__(self):
        self.start_timestamp = time.time()

        self.event_id = ''

        # invoke, add_user, ...
        self.event_name = ''

        # S3, Lambda, Twilio
        self.event_type = self.EVENT_TYPE

        # botocore, requests, ...
        self.event_module = self.EVENT_MODULE

        self.end_timestamp = 0
        self.error_code = ErrorCode.OK
        self.metadata = {}

    def dictify(self):
        return {
            'id': self.event_id,
            'start_timestamp': self.start_timestamp,
            'end_timestamp': self.end_timestamp,
            'event_name': self.event_name,
            'event_type': self.event_type,
            'event_module': self.event_module,
            'error_code': self.error_code,
            'metadata': self.metadata,
        }

    def terminate(self):
        self.end_timestamp = time.time()

    def add_event(self):
        self.terminate()
        tracer.operations.append(self)
