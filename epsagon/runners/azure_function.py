"""
Runner and Triggers for Azure Functions
"""

from __future__ import absolute_import
from ..event import BaseEvent
from ..trace import tracer
import os


##########
# runner #
##########

class AzureFunctionRunner(BaseEvent):
    """
    Represents epsagon azure event (main runner)
    """

    EVENT_MODULE = 'runner'
    EVENT_TYPE = 'azure_function'

    def __init__(self):
        super(AzureFunctionRunner, self).__init__()
        self.resource_name = os.environ['EXECUTION_CONTEXT_FUNCTIONNAME']
        self.event_operation = 'Invoke'
        self.event_id = os.environ['EXECUTION_CONTEXT_INVOCATIONID']

        self.metadata = {
            'region': os.environ['REGION_NAME'],
            'cold_start': 'False',
        }

    def set_error(self, error_code, exception, traceback):
        tracer.error_code = error_code
        self.error_code = error_code
        self.metadata['exception'] = repr(exception)
        self.metadata['traceback'] = traceback
