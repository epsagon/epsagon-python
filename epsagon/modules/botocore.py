"""
botocore patcher module
"""

from __future__ import absolute_import

import traceback

import wrapt
from botocore.exceptions import ClientError

from epsagon.trace import tracer
from ..events.botocore import BotocoreEventFactory


def _botocore_wrapper(wrapped, instance, args, kwargs):
    response = None
    exception = None
    try:
        response = wrapped(*args, **kwargs)
        return response
    except ClientError as exception:
        raise exception
    finally:
        try:
            BotocoreEventFactory.create_event(
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
        'botocore.client',
        'BaseClient._make_api_call',
        _botocore_wrapper
    )
