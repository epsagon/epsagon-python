"""
logging patcher module.
"""

from __future__ import absolute_import
from functools import partial
import os
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
    if (os.getenv(
            'EPSAGON_DISABLE_LOGGING_ERRORS'
    ) or '').upper() == 'TRUE':
        trace_factory.set_error(*args)
    return wrapped(*args, **kwargs)


def _get_log_id():
    """
    retrieve or generate the log id for this trace
    """
    return trace_factory.get_log_id()


def _epsagon_trace_id_wrapper(msg_index, wrapped, _instance, args, kwargs):
    """
    Wrapper for logging module.
    :param wrapped: wrapt's wrapped
    :param _instance: wrapt's instance, unused.
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    :return: None
    """
    if trace_factory.is_logging_tracing_enabled():
        msg = ' '.join([_get_log_id(), args[msg_index]])
        args = args[0:msg_index] + (msg,) + args[(msg_index+1):]
    return wrapped(*args, **kwargs)


def patch():
    """
    Patch module.
    :return: None
    """
    wrapt.wrap_function_wrapper('logging', 'exception', _wrapper)
    wrapt.wrap_function_wrapper('logging', 'Logger.exception', _wrapper)
    wrapt.wrap_function_wrapper(
        'logging', 'Logger.log', partial(_epsagon_trace_id_wrapper, 1))
    # wrapt.wrap_function_wrapper(
    #     'builtins', 'print', partial(_epsagon_trace_id_wrapper, 0))
    for log_function in ['info', 'debug', 'error',
                         'warning', 'exception', 'critical']:
        wrapt.wrap_function_wrapper(
            'logging', 'Logger.' + log_function,
            partial(_epsagon_trace_id_wrapper, 0))
