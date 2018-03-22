"""
Runner for AWS Lambda.
"""

from __future__ import absolute_import
import os
from ..event import BaseEvent
from .. import constants


class LambdaRunner(BaseEvent):
    """
    Represents Lambda event runner.
    """

    ORIGIN = 'runner'
    RESOURCE_TYPE = 'lambda'
    OPERATION = 'invoke'

    def __init__(self, start_time, context):
        """
        Initialize.
        :param start_time: event's start time (epoch)
        :param context: Lambda's context (passed from entry point)
        """

        super(LambdaRunner, self).__init__(start_time)

        self.event_id = context.aws_request_id
        self.resource['name'] = context.function_name
        self.resource['operation'] = self.OPERATION
        self.resource['metadata'] = {
            'log_stream_name': context.log_stream_name,
            'log_group_name': context.log_group_name,
            'function_version': context.function_version,
            'memory': context.memory_limit_in_mb,
            'cold_start': constants.COLD_START,
            'region': os.environ.get('AWS_REGION', ''),
        }

    def add_step_data(self, steps_dict):
        """
        Add steps function data.
        :param steps_dict: The steps dictionary to add.
        """
        self.resource['steps_dict'] = steps_dict
