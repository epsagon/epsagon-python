"""
grpc patcher module
"""

from __future__ import absolute_import
import wrapt
from ..events.grpc import GRPCEventFactory


def _grpc_wrapper(wrapped, instance, args, kwargs):
    response = None
    exception = None
    try:
        response = wrapped(*args, **kwargs)
        return response
    except Exception as exception:
        raise exception
    finally:
        GRPCEventFactory.create_event(wrapped, instance, args, kwargs, response, exception)


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
