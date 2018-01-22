"""
requests patcher module
"""

from __future__ import absolute_import
import wrapt
import traceback
from ..trace import tracer
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
        try:
            RequestsEventFactory.create_event(
                wrapped,
                instance,
                args,
                kwargs,
                response,
                exception
            )
        except Exception as e:
            exception_dict = {
                'message': e.message,
                'args': e.args,
                'traceback': traceback.format_exc()
            }
            tracer.exceptions.append(exception_dict)


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
