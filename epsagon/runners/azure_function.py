"""
Runner for Azure Functions.
"""

from __future__ import absolute_import
import os
from ..event import BaseEvent


class AzureFunctionRunner(BaseEvent):
    """
    Represents Azure function event runner.
    """

    ORIGIN = 'runner'
    RESOURCE_TYPE = 'azure_function'
    OPERATION = 'Invoke'

    def __init__(self, start_time):
        """
        Initialize.
        :param start_time: event's start time (epoch)
        """

        super(AzureFunctionRunner, self).__init__(start_time)

        self.event_id = os.getenv('EXECUTION_CONTEXT_INVOCATIONID', '')
        self.resource['name'] = os.getenv(
            'EXECUTION_CONTEXT_FUNCTIONNAME',
            ''
        )
        self.resource['operation'] = self.OPERATION

        self.resource['metadata'] = {
            'region': os.getenv('REGION_NAME', ''),
            'memory': os.getenv('WEBSITE_MEMORY_LIMIT_MB', ''),
        }
