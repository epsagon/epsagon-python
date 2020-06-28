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

    def __init__(self, start_time, context):
        """
        Initialize.
        :param start_time: event's start time (epoch)
        :param context: function's context, azure.functions.Context
        """

        super(AzureFunctionRunner, self).__init__(start_time)

        self.event_id = context.invocation_id
        self.resource['name'] = context.function_name
        self.resource['operation'] = self.OPERATION

        self.resource['metadata'].update({
            'azure.resource_group': os.getenv('ResourceGroupName', ''),
            'azure.location': os.getenv('Location', ''),
            'azure.function.log': os.getenv('LOGNAME', ''),
            'azure.function.app': os.getenv('WEBSITE_SITE_NAME', ''),
        })
