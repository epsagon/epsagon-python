"""
Runner for Tencent SCF.
"""

from __future__ import absolute_import
from ..event import BaseEvent
from .. import constants
from ..common import ErrorCode


class TencentFunctionRunner(BaseEvent):
    """
    Represents Tencent SCF event runner.
    """
    ORIGIN = 'runner'
    RESOURCE_TYPE = 'tencent_function'
    OPERATION = 'invoke'

    def __init__(self, start_time, context):
        """
        Initialize.
        :param start_time: event's start time (epoch)
        :param context: SCF's context (passed from entry point)
        """
        super(TencentFunctionRunner, self).__init__(start_time)

        # Creating a unique ID for local runs.
        self.event_id = context['request_id']
        self.resource['name'] = context['function_name']
        self.resource['operation'] = self.OPERATION

        self.resource['metadata'].update({
            'tencent.scf.version': context['function_version'],
            'tencent.scf.memory': context['memory_limit_in_mb'],
            'tencent.scf.cold_start': constants.COLD_START,
            'tencent.namespace': context['namespace'],
            'tencent.uin': context['tencentcloud_uin'],
            'tencent.app_id': context['tencentcloud_appid'],
            'tencent.region': context['tencentcloud_region'],
        })

    def set_timeout(self):
        """
        Sets timeout error code.
        :return: None
        """
        # Don't override exceptions
        if self.error_code != ErrorCode.EXCEPTION:
            self.error_code = ErrorCode.TIMEOUT
