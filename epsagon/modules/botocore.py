"""
botocore patcher module.
"""

from __future__ import absolute_import
import json
from uuid import uuid4
import wrapt
from epsagon.modules.general_wrapper import wrapper
from epsagon.constants import STEP_DICT_NAME
from ..events.botocore import (
    BotocoreEventFactory,
    BotocoreStepFunctionEvent
)
from .requests import _wrapper as _requests_wrapper


def _wrapper(wrapped, instance, args, kwargs):
    """
    General wrapper for botocore instrumentation.
    :param wrapped: wrapt's wrapped
    :param instance: wrapt's instance
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    :return: None
    """
    instance_type = instance.__class__.__name__.lower()
    if instance_type == BotocoreStepFunctionEvent.RESOURCE_TYPE:
        handle_stepfunc_args(args)

    return wrapper(BotocoreEventFactory, wrapped, instance, args, kwargs)


def add_steps_dict_to_request(request_args, params_property_name):
    machine_input = json.loads(request_args[params_property_name])
    machine_input[STEP_DICT_NAME] = {'id': str(uuid4()), 'step_num': -1}
    request_args[params_property_name] = json.dumps(machine_input)


def handle_stepfunc_args(args):
    try:
        event_operation, request_args = args

        if event_operation == 'StartExecution':
            add_steps_dict_to_request(request_args, 'input')
        elif event_operation == 'SendTaskSuccess':
            add_steps_dict_to_request(request_args, 'output')
    except Exception:  # pylint: disable=broad-except
        pass


def patch():
    """
    Patch module.
    :return: None
    """

    wrapt.wrap_function_wrapper(
        'botocore.client',
        'BaseClient._make_api_call',
        _wrapper
    )

    # botocore no longer vendor requests in new version
    # https://github.com/boto/botocore/pull/1829
    wrapt.wrap_function_wrapper(
        'botocore.vendored.requests',
        'Session.send',
        _requests_wrapper
    )
