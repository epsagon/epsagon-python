"""
requests patcher module.
"""

from __future__ import absolute_import
import wrapt
from epsagon.modules.general_wrapper import wrapper
from ..events.requests import RequestsEventFactory


def _wrapper(wrapped, instance, args, kwargs):
    """
    General wrapper for requests instrumentation.
    :param wrapped: wrapt's wrapped
    :param instance: wrapt's instance
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    :return: None
    """

    return wrapper(RequestsEventFactory, wrapped, instance, args, kwargs)


def patch():
    """
    Patch module.
    :return: None
    """

    wrapt.wrap_function_wrapper(
        'requests',
        'Session.send',
        _wrapper
    )
