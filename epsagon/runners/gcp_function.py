"""
Runner for Google Functions.

"""

from __future__ import absolute_import
import os
from uuid import uuid4
from ..event import BaseEvent
from .. import constants


class GoogleFunctionRunner(BaseEvent):
    """
    Represents Google function event runner.
    """

    ORIGIN = 'runner'
    RESOURCE_TYPE = 'google_function'
    OPERATION = 'Invoke'

    def __init__(self, start_time):
        """
        Initialize.
        :param start_time: event's start time (epoch)
        """

        super(GoogleFunctionRunner, self).__init__(start_time)

        self.event_id = 'gcp_{}'.format(str(uuid4()))
        self.resource['name'] = os.getenv(
            'FUNCTION_NAME',
            ''
        )
        self.resource['operation'] = self.OPERATION

        self.resource['metadata'].update({
            'gcp_project': os.getenv('GCP_PROJECT', ''),
            'function_version': os.getenv('X_GOOGLE_FUNCTION_VERSION', ''),
            'memory':  os.getenv('FUNCTION_MEMORY_MB', ''),
            'cold_start': constants.COLD_START,
            'region': os.getenv('FUNCTION_REGION', ''),
            'supervisor_hostname': os.getenv('SUPERVISOR_HOSTNAME', ''),
            'supervisor_internal_port': os.getenv(
                'SUPERVISOR_INTERNAL_PORT', ''
            ),
            'virtual_env': os.getenv('VIRTUAL_ENV', ''),
            'worker_port': os.getenv('WORKER_PORT', ''),
        })
