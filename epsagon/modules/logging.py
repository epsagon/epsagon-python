"""
logging patcher module.
"""

from __future__ import absolute_import
from functools import partial
import uuid
import os
import wrapt
from ..trace import trace_factory


LOG_ID_LABEL_NAME = 'epsagon_log_id'


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
    log_id = trace_factory.get_label(LOG_ID_LABEL_NAME)
    if not log_id:
        log_id = uuid.uuid4().hex
        trace_factory.add_label(LOG_ID_LABEL_NAME, log_id)
    return log_id


def _epsagon_log_id_wrapper(msg_index, wrapped, _instance, args, kwargs):
    """
    Wrapper for logging module.
    :param wrapped: wrapt's wrapped
    :param _instance: wrapt's instance, unused.
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    :return: None
    """
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
        'logging', 'Logger.log', partial(_epsagon_log_id_wrapper, 1))
    for log_function in ['info', 'debug', 'error',
                         'warning', 'exception', 'critical']:
        wrapt.wrap_function_wrapper(
            'logging', 'Logger.' + log_function,
            partial(_epsagon_log_id_wrapper, 0))
