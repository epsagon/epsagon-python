"""
httplib2 patcher module.
"""

from __future__ import absolute_import
import wrapt
from epsagon.modules.general_wrapper import wrapper
from ..events.httplib2 import Httplib2EventFactory


def _wrapper(wrapped, instance, args, kwargs):
    """
    General wrapper for httplib2 instrumentation.
    :param wrapped: wrapt's wrapped
    :param instance: wrapt's instance
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    :return: None
    """

    return wrapper(Httplib2EventFactory, wrapped, instance, args, kwargs)


def patch():
    """
    Patch module.
    :return: None
    """

    wrapt.wrap_function_wrapper(
        'httplib2',
        'Http.request',
        _wrapper
    )
