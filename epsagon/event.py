"""

"""

from __future__ import absolute_import
import time
from .common import ErrorCode


class BaseEvent(object):
    """
    Represents base trace's event
    """

    EVENT_MODULE = 'base'
    RESOURCE_TYPE = 'generic'

    def __init__(self):
        self.start_timestamp = time.time()

        self.event_id = ''

        # my-resize, traces-stream, ...
        self.resource_name = ''

        # invoke, add_user, ...
        self.event_operation = ''

        # S3, Lambda, Twilio
        self.resource_type = self.RESOURCE_TYPE

        # botocore, requests, ...
        self.event_module = self.EVENT_MODULE

        self.end_timestamp = 0
        self.error_code = ErrorCode.OK
        self.metadata = {}

    @staticmethod
    def load_from_dict(event_data):
        event = BaseEvent()
        event.event_id = event_data['event_id']
        event.resource_name = event_data['resource_name']
        event.event_operation = event_data['event_operation']
        event.resource_type = event_data['resource_type']
        event.event_module = event_data['event_module']
        event.start_timestamp = event_data['start_timestamp']
        event.end_timestamp = event_data['end_timestamp']
        event.error_code = event_data['error_code']
        event.metadata = event_data['metadata']
        return event

    def dictify(self):
        return {
            'event_id': self.event_id,
            'start_timestamp': self.start_timestamp,
            'end_timestamp': self.end_timestamp,
            'resource_name': self.resource_name,
            'event_operation': self.event_operation,
            'resource_type': self.resource_type,
            'event_module': self.event_module,
            'error_code': self.error_code,
            'metadata': self.metadata,
        }

    def dictify_dynamodb(self, transaction_id, app_name):
        """
        Preparing dict that ready for dynamodb (no empty string and no floats).
        Adding transaction ID and app_name for easier extraction
        :return: dict
        """
        event = self.dictify()
        event['start_timestamp'] = str(self.start_timestamp)
        event['end_timestamp'] = str(self.end_timestamp)
        event['transaction_id'] = transaction_id
        event['app_name'] = app_name
        return event

    def terminate(self):
        self.end_timestamp = time.time()

    def update_response(self, response):
        pass

    def set_error(self):
        self.error_code = ErrorCode.ERROR
