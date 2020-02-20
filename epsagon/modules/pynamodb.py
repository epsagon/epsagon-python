"""
PynamoDB patcher module.
"""

from __future__ import absolute_import
import wrapt
from epsagon.modules.general_wrapper import wrapper
from ..events.pynamodb import PynamoDBEventAdapter, PynamoDBVendoredEventAdapter


def _vendored_wrapper(wrapped, instance, args, kwargs):
    """
    General wrapper for PynamoDB instrumentation.
    :param wrapped: wrapt's wrapped
    :param instance: wrapt's instance
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    :return: None
    """

    # Skip non DynamoDB requests
    if 'https://dynamodb.' not in args[0].url:
        return wrapped(*args, **kwargs)

    return wrapper(
        PynamoDBVendoredEventAdapter,
        wrapped,
        instance,
        args,
        kwargs
    )


def _wrapper(wrapped, instance, args, kwargs):
    """
    General wrapper for PynamoDB instrumentation.
    :param wrapped: wrapt's wrapped
    :param instance: wrapt's instance
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    :return: None
    """
    return wrapper(PynamoDBEventAdapter, wrapped, instance, args, kwargs)


def patch():
    """
    Patch module.
    :return: None
    """
    try:
        wrapt.wrap_function_wrapper(
            'pynamodb.connection.base',
            'Connection._make_api_call',
            _wrapper
        )
    except AttributeError:
        pass

    try:
        wrapt.wrap_function_wrapper(
            'botocore.vendored.requests.sessions',
            'Session.send',
            _vendored_wrapper
        )
    except AttributeError:
        pass
