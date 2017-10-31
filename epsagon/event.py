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

        # my-resize, traces-stream, ...
        self.resource_name = ''

        # invoke, add_user, ...
        self.event_operation = ''

        # S3, Lambda, Twilio
        self.event_type = self.EVENT_TYPE

        # botocore, requests, ...
        self.event_module = self.EVENT_MODULE

        self.end_timestamp = 0
        self.error_code = ErrorCode.OK
        self.metadata = {}

    @staticmethod
    def load_from_dict(event_data):
        event = BaseEvent()
        event.event_id = event_data['id']
        event.resource_name = event_data['resource_name']
        event.event_operation = event_data['event_operation']
        event.event_type = event_data['event_type']
        event.event_module = event_data['event_module']
        event.start_timestamp = event_data['start_timestamp']
        event.end_timestamp = event_data['end_timestamp']
        event.error_code = event_data['error_code']
        event.metadata = event_data['metadata']
        return event

    def dictify(self):
        return {
            'id': self.event_id,
            'start_timestamp': self.start_timestamp,
            'end_timestamp': self.end_timestamp,
            'resource_name': self.resource_name,
            'event_operation': self.event_operation,
            'event_type': self.event_type,
            'event_module': self.event_module,
            'error_code': self.error_code,
            'metadata': self.metadata,
        }

    def dictify_dynamodb(self, transaction_id):
        """
        Preparing dict that ready for dynamodb (no empty string and no floats).
        Adding transaction ID
        :return: dict
        """
        event = self.dictify()
        event['start_timestamp'] = str(self.start_timestamp)
        event['end_timestamp'] = str(self.end_timestamp)
        event['transaction_id'] = transaction_id
        return event

    def terminate(self):
        self.end_timestamp = time.time()

    def add_event(self):
        self.terminate()
        tracer.operations.append(self)
