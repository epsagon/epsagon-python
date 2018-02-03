"""
grpc patcher module.
"""

from __future__ import absolute_import
import wrapt
from epsagon.modules.general_wrapper import wrapper
from ..events.grpc import GRPCEventFactory


def _wrapper(wrapped, instance, args, kwargs):
    """
    General wrapper for grpc instrumentation.
    :param wrapped: wrapt's wrapped
    :param instance: wrapt's instance
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    :return: None
    """

    return wrapper(GRPCEventFactory, wrapped, instance, args, kwargs)


def patch():
    """
    Patch module.
    :return: None
    """

    wrapt.wrap_function_wrapper(
        'grpc._channel',
        '_UnaryUnaryMultiCallable.__call__',
        _wrapper
    )
