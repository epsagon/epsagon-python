"""
grpc patcher module
"""

from __future__ import absolute_import
import wrapt
from ..events.grpc import GRPCEventFactory


def _grpc_wrapper(wrapped, instance, args, kwargs):
    event = GRPCEventFactory.factory(instance, args)
    try:
        parsed_response = wrapped(*args, **kwargs)
        event.post_update(parsed_response)
        return parsed_response
    except Exception as exception:
        raise exception
    finally:
        event.add_event()


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
