"""
greengrasssdk patcher module.
"""

from __future__ import absolute_import
import wrapt
from epsagon.modules.general_wrapper import wrapper
from ..events.greengrasssdk import GreengrassEventFactory


def _wrapper(wrapped, instance, args, kwargs):
    """
    General wrapper for greengrasssdk instrumentation.
    :param wrapped: wrapt's wrapped
    :param instance: wrapt's instance
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    :return: None
    """
    return wrapper(GreengrassEventFactory, wrapped, instance, args, kwargs)


def patch():
    """
    Patch module.
    :return: None
    """
    wrapt.wrap_function_wrapper(
        'greengrasssdk.IoTDataPlane',
        'Client.publish',
        _wrapper
    )
