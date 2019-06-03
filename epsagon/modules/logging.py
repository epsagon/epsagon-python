"""
logging patcher module.
"""

from __future__ import absolute_import
import wrapt
from epsagon.modules.general_wrapper import wrapper
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
    response = wrapped(*args, **kwargs)
    return response


def patch():
    """
    Patch module.
    :return: None
    """
    wrapt.wrap_function_wrapper(
        'logging',
        'exception',
        _wrapper
    )
