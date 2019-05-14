"""
Tornado patcher module.
"""

from __future__ import absolute_import
import time
import traceback
import wrapt
import epsagon.trace
from epsagon.runners.tornado import TornadoRunner
from epsagon.wrappers.http_filters import ignore_request


class TornadoWrapper(object):
    """
    Wraps Tornado web framework to get requests.
    """
    RUNNER = None

    @classmethod
    def before_request(cls, wrapped, instance, args, kwargs):
        """
        Runs when new request comes in.
        :param wrapped: wrapt's wrapped
        :param instance: wrapt's instance
        :param args: wrapt's args
        :param kwargs: wrapt's kwargs
        """
        try:
            epsagon.trace.trace_factory.get_or_create_trace().prepare()
            ignored = ignore_request('', instance.request.path)
            if not ignored:
                cls.RUNNER = TornadoRunner(time.time(), instance.request)
        except Exception as instrumentation_exception:  # pylint: disable=W0703
            epsagon.trace.trace_factory.add_exception(
                instrumentation_exception,
                traceback.format_exc()
            )
        return wrapped(*args, **kwargs)

    @classmethod
    def after_request(cls, wrapped, instance, args, kwargs):
        """
        Runs after first process of response.
        :param wrapped: wrapt's wrapped
        :param instance: wrapt's instance
        :param args: wrapt's args
        :param kwargs: wrapt's kwargs
        """
        trace = epsagon.trace.trace_factory.get_or_create_trace()
        try:
            content = instance._headers.get(  # pylint: disable=protected-access
                'Content-Type',
                ''
            )
            ignored = ignore_request(content, '')
            if not ignored and cls.RUNNER:
                cls.RUNNER.update_response(instance)
                trace.add_event(cls.RUNNER)
                trace.send_traces()
            trace.prepare()
        except Exception as instrumentation_exception:  # pylint: disable=W0703
            trace.add_exception(
                instrumentation_exception,
                traceback.format_exc()
            )
        cls.RUNNER = None
        return wrapped(*args, **kwargs)

    @classmethod
    def collect_exception(cls, wrapped, _, args, kwargs):
        """
        Runs after first process of response.
        :param wrapped: wrapt's wrapped
        :param _: wrapt's instance
        :param args: wrapt's args
        :param kwargs: wrapt's kwargs
        """
        try:
            if cls.RUNNER:
                _, exception, _ = args
                cls.RUNNER.set_exception(exception, traceback.format_exc())
        except Exception as instrumentation_exception:  # pylint: disable=W0703
            epsagon.trace.trace_factory.add_exception(
                instrumentation_exception,
                traceback.format_exc()
            )

        return wrapped(*args, **kwargs)


def patch():
    """
    Patch module.
    """

    wrapt.wrap_function_wrapper(
        'tornado.web',
        'RequestHandler._execute',
        TornadoWrapper.before_request
    )
    wrapt.wrap_function_wrapper(
        'tornado.web',
        'RequestHandler.on_finish',
        TornadoWrapper.after_request
    )
    wrapt.wrap_function_wrapper(
        'tornado.web',
        'RequestHandler.log_exception',
        TornadoWrapper.collect_exception
    )
