"""
logging patcher module.
"""

from __future__ import absolute_import
import wrapt
from ..trace import trace_factory


def _wrapper(wrapped, _instance, args, kwargs):
    """
    Wrapper for logging module.
    :param wrapped: wrapt's wrapped
    :param _instance: wrapt's instance, unused.
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    :return: None
    """
    trace_factory.set_error(*args)
    return wrapped(*args, **kwargs)


def patch():
    """
    Patch module.
    :return: None
    """
    wrapt.wrap_function_wrapper('logging', 'exception', _wrapper)
    wrapt.wrap_function_wrapper('logging', 'Logger.exception', _wrapper)
