"""
logging patcher module.
"""

from __future__ import absolute_import

import json
import os
from functools import partial

import wrapt

from ..trace import trace_factory
from ..utils import print_debug

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
    if not os.getenv('EPSAGON_DISABLE_LOGGING_ERRORS', '').upper() == 'TRUE':
        try:
            message = args[0] % args[1:]
            trace_factory.set_error(message)
        except Exception:  # pylint: disable=broad-except
            print_debug('Could not capture exception from log: {}'.format(
                args
            ))

    return wrapped(*args, **kwargs)


def _add_log_id(trace_log_id, msg):
    """
    adds log id to the msg
    """
    try:
        # Check if message is in json format
        json_log = json.loads(msg)
        json_log['epsagon'] = {'trace_id': trace_log_id}
        return json.dumps(json_log)
    except Exception:   # pylint: disable=broad-except
        # message is a regular string, add the ID to the beginning
        if not isinstance(msg, str):
            msg = str(msg)
        return ' '.join([trace_log_id, msg])


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
    trace_log_id = trace_factory.get_log_id()

    if not trace_log_id:
        return wrapped(*args, **kwargs)

    try:
        message = _add_log_id(trace_log_id, args[msg_index])
    except Exception:   # pylint: disable=broad-except
        # total failure to add log id
        return wrapped(*args, **kwargs)
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
    if trace_factory.is_logging_tracing_enabled():
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
