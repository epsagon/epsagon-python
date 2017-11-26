"""

"""

from __future__ import absolute_import
import time
from uuid import uuid4
import boto3
try:
    import ujson as json
except:
    # Support azure for now
    import json
from .common import ErrorCode
from .constants import REGION, TRACE_COLLECTOR_STREAM, __version__


kinesis = boto3.client(
    'kinesis',
    aws_access_key_id='AKIAJCGBKUPQWB663YRA',
    aws_secret_access_key='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',
    region_name=REGION
)


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
        self.metadata = {
            'version': __version__,
        }

    def prepare(self):
        if self.token == '':
            print 'Epsagon Error: Please initialize token, data won\'t be sent.'
        self.trace_id = str(uuid4())
        self.start_timestamp = time.time()
        self.end_timestamp = 0
        self.error_code = ErrorCode.OK
        self.trigger = None
        self.runner = None
        self.operations = []

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
            'metadata': self.metadata,
            'trigger': None if self.trigger is None else self.trigger.dictify(),
            'runner': self.runner.dictify(),
            'operations': [operation.dictify() for operation in self.operations]
        }

    def send_traces(self):
        if self.token == '':
            return

        if self.end_timestamp == 0:
            self.end_timestamp = time.time()

        try:
            kinesis.put_record(
                StreamName=TRACE_COLLECTOR_STREAM,
                Data=json.dumps(self.dictify()),
                PartitionKey='0',
            )
        except Exception as exception:
            print 'Epsagon Error: Could not send traces {}'.format(exception.message)


tracer = Trace()
