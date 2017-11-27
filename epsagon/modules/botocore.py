"""
botocore patcher module
"""

from __future__ import absolute_import
import wrapt
from botocore.exceptions import ClientError
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
        BotocoreEventFactory.create_event(wrapped, instance, args, kwargs, response, exception)


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
