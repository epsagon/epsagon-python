"""
requests patcher module.

This is deprecated now that we have urllib3 support as requests is using urllib3
under the hood.
This is left here both as future reference and because it is used in the
botocore module that has a similar interface.
"""

from __future__ import absolute_import
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

    # wrapt.wrap_function_wrapper(
    #     'requests',
    #     'Session.send',
    #     _wrapper
    # )
