"""
logging patcher module.
"""

from __future__ import absolute_import

import json
import os
from functools import partial

import wrapt

from ..trace import trace_factory

LOGGING_FUNCTIONS = (
    'info',
    'debug',
    'error',
    'warning',
    'exception',
    'critical'
)


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


def _epsagon_trace_id_wrapper(msg_index, wrapped, _instance, args, kwargs):
    """
    Wrapper for logging module.
    :param msg_index: the index of the log message in args
        (since Logger.log also gets `level`)
    :param wrapped: wrapt's wrapped
    :param _instance: wrapt's instance, unused.
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    :return: None
    """
    if trace_factory.is_logging_tracing_enabled():
        trace_log_id = trace_factory.get_log_id()

        if not trace_log_id:
            return wrapped(*args, **kwargs)

        try:
            # Check if message is in json format
            json_log = json.loads(args[msg_index])
            json_log['epsagon'] = {'trace_id': trace_log_id}
            message = json.dumps(json_log)
        except Exception:  # pylint: disable=broad-except
            # message is a regular string, add the ID to the beginning
            message = ' '.join([trace_log_id, args[msg_index]])
        args = (
            args[0:msg_index] +
            (message,) +
            args[(msg_index + 1):]
        )
    return wrapped(*args, **kwargs)


def patch():
    """
    Patch module.
    :return: None
    """
    # Automatically capture exceptions from logging
    wrapt.wrap_function_wrapper('logging', 'exception', _wrapper)
    wrapt.wrap_function_wrapper('logging', 'Logger.exception', _wrapper)

    # Instrument logging with Epsagon trace ID
    wrapt.wrap_function_wrapper(
        'logging',
        'Logger.log',
        partial(_epsagon_trace_id_wrapper, 1)
    )
    for log_function in LOGGING_FUNCTIONS:
        wrapt.wrap_function_wrapper(
            'logging',
            'Logger.{}'.format(log_function),
            partial(_epsagon_trace_id_wrapper, 0)
        )

    # Instrument print function is disabled
    # wrapt.wrap_function_wrapper(
    #   'builtins',
    #   'print',
    #   partial(_epsagon_trace_id_wrapper, 0)
    # )
