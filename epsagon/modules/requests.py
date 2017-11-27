"""
requests patcher module
"""

from __future__ import absolute_import
import wrapt
from ..events.requests import RequestsEventFactory


def _request_wrapper(wrapped, instance, args, kwargs):
    response = None
    exception = None
    try:
        response = wrapped(*args, **kwargs)
        return response
    except Exception as exception:
        raise exception
    finally:
        RequestsEventFactory.create_event(wrapped, instance, args, kwargs, response, exception)


def patch():
    """
    patch module
    :return: None
    """
    wrapt.wrap_function_wrapper(
        'requests',
        'Session.send',
        _request_wrapper
    )
