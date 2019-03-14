"""
botocore patcher module.
"""

from __future__ import absolute_import
import wrapt
from epsagon.modules.general_wrapper import wrapper
from ..events.botocore import BotocoreEventFactory
from .requests import _wrapper as _requests_wrapper


def _wrapper(wrapped, instance, args, kwargs):
    """
    General wrapper for botocore instrumentation.
    :param wrapped: wrapt's wrapped
    :param instance: wrapt's instance
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    :return: None
    """
    return wrapper(BotocoreEventFactory, wrapped, instance, args, kwargs)


def patch():
    """
    Patch module.
    :return: None
    """

    wrapt.wrap_function_wrapper(
        'botocore.client',
        'BaseClient._make_api_call',
        _wrapper
    )

    wrapt.wrap_function_wrapper(
        'botocore.vendored.requests',
        'Session.send',
        _requests_wrapper
    )
