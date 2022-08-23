"""
pyqldb patcher module
"""
from __future__ import absolute_import
import wrapt
from epsagon.modules.general_wrapper import wrapper
from ..events.pyqldb import QldbEventFactory


def _wrapper(wrapped, instance, args, kwargs):
    """
    General wrapper for Pyqldb instrumentation.
    :param wrapped: wrapt's wrapped
    :param instance: wrapt's instance
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    :return: None
    """
    return wrapper(QldbEventFactory, wrapped, instance, args, kwargs)


def patch():
    """
    patch module.
    :return: None
    """
    wrapt.wrap_function_wrapper(
        'pyqldb.execution.executor',
        'Executor.execute_statement',
        _wrapper
    )
