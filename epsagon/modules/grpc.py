"""
grpc patcher module
"""
from __future__ import absolute_import

import wrapt
from epsagon.modules.general_wrapper import wrapper
from ..events.grpc import GRPCEventFactory


def _grpc_wrapper(wrapped, instance, args, kwargs):
    return wrapper(
        GRPCEventFactory,
        wrapped,
        instance,
        args,
        kwargs
    )


def patch():
    """
    patch module
    :return: None
    """
    wrapt.wrap_function_wrapper(
        'grpc._channel',
        '_UnaryUnaryMultiCallable.__call__',
        _grpc_wrapper
    )
