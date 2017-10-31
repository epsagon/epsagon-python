"""
botocore patcher module
"""

from __future__ import absolute_import
import wrapt
from botocore.exceptions import ClientError
from ..events.botocore import BotocoreEventFactory


def _botocore_wrapper(wrapped, instance, args, kwargs):
    event = BotocoreEventFactory.factory(instance, args)
    try:
        parsed_response = wrapped(*args, **kwargs)
        event.post_update(parsed_response)
        return parsed_response
    except ClientError as exception:
        event.set_error(exception.response['Error'])
        raise exception
    finally:
        event.add_event()


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
