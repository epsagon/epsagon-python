"""
Tornado patcher module.
"""

from __future__ import absolute_import
import wrapt
import epsagon.trace
import time
from epsagon.runners.tornado import TornadoRunner

RUNNER = None


def _before_request(wrapped, instance, args, kwargs):
    """
    Runs when new request comes in.
    :param wrapped: wrapt's wrapped
    :param instance: wrapt's instance
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    :return: None
    """
    global RUNNER
    epsagon.trace.tracer.prepare()
    RUNNER = TornadoRunner(time.time(), instance.request)
    return wrapped(*args, *kwargs)


def _after_request(wrapped, instance, args, kwargs):
    """
    Runs after first process of response.
    :param wrapped: wrapt's wrapped
    :param instance: wrapt's instance
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    :return: None
    """
    RUNNER.update_response(instance)
    epsagon.trace.tracer.add_event(RUNNER)
    epsagon.trace.tracer.send_traces()
    epsagon.trace.tracer.prepare()
    return wrapped(*args, *kwargs)


def patch():
    """
    Patch module.
    :return: None
    """

    wrapt.wrap_function_wrapper(
        'tornado.web',
        'RequestHandler._execute',
        _before_request
    )
    wrapt.wrap_function_wrapper(
        'tornado.web',
        'RequestHandler.on_finish',
        _after_request
    )
    # wrapt.wrap_function_wrapper('tornado.web', 'RequestHandler.log_exception', _wrapper)
