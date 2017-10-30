"""
requests patcher module
"""

from __future__ import absolute_import
import wrapt
from ..events.requests import RequestsEventFactory


def _request_wrapper(wrapped, _, args, kwargs):
    event = RequestsEventFactory.factory(args)
    try:
        response = wrapped(*args, **kwargs)
        event.post_update(response)
        return response
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
        'requests',
        'Session.send',
        _request_wrapper
    )
