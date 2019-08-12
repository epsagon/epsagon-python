"""
Tornado patcher module.
"""

from __future__ import absolute_import
import time
import traceback
import uuid
from functools import partial
import wrapt
import epsagon.trace
from epsagon.runners.tornado import TornadoRunner
from epsagon.wrappers.http_filters import ignore_request
from epsagon.utils import collect_container_metadata

TORNADO_TRACE_ID = 'epsagon_tornado_trace_key'


class TornadoWrapper(object):
    """
    Wraps Tornado web framework to get requests.
    """
    RUNNERS = {}

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
            ignored = ignore_request('', instance.request.path)
            if not ignored:
                unique_id = str(uuid.uuid4())
                trace = epsagon.trace.trace_factory.get_or_create_trace(
                    unique_id=unique_id
                )

                trace.prepare()

                setattr(instance, TORNADO_TRACE_ID, unique_id)

                cls.RUNNERS[unique_id] = (
                    TornadoRunner(time.time(), instance.request)
                )

                # Collect metadata in case this is a container.
                metadata = collect_container_metadata()
                if metadata:
                    cls.RUNNERS[unique_id].resource['metadata']['ECS'] = (
                        metadata
                    )

                trace.set_runner(cls.RUNNERS[unique_id])
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
        res = wrapped(*args, **kwargs)
        try:
            unique_id = getattr(instance, TORNADO_TRACE_ID)
            tornado_runner = cls.RUNNERS.pop(unique_id)

            trace = epsagon.trace.trace_factory.get_or_create_trace(
                unique_id=unique_id
            )

            content = instance._headers.get(  # pylint: disable=protected-access
                'Content-Type',
                ''
            )
            ignored = ignore_request(content, '')
            if not ignored:
                tornado_runner.update_response(instance)
                trace.send_traces()

            trace.prepare()

        except Exception as instrumentation_exception:  # pylint: disable=W0703
            trace.add_exception(
                instrumentation_exception,
                traceback.format_exc()
            )
        return res

    @classmethod
    def collect_exception(cls, wrapped, instance, args, kwargs):
        """
        Runs after first process of response.
        :param wrapped: wrapt's wrapped
        :param _: wrapt's instance
        :param args: wrapt's args
        :param kwargs: wrapt's kwargs
        """
        try:
            unique_id = getattr(instance, TORNADO_TRACE_ID, None)

            if unique_id and cls.RUNNERS.get(unique_id):
                _, exception, _ = args
                cls.RUNNERS[unique_id].set_exception(
                    exception, traceback.format_exc()
                )
        except Exception as instrumentation_exception:  # pylint: disable=W0703
            epsagon.trace.trace_factory.add_exception(
                instrumentation_exception,
                traceback.format_exc()
            )

        return wrapped(*args, **kwargs)

    @classmethod
    def run_callback(cls, wrapped, _, args, kwargs):
        """
        Instrument run_callback in the event loop
        :param wrapped: wrapt's wrapped
        :param _: wrapt's instnace
        :param args: wrapper arguments containing the callback function
        :param kwargs: kwargs arguments
        :return: callback wrapped after selecting active trace
        """
        try:
            func = args[0]
            if isinstance(func, partial):
                func = func.func
            unique_id = getattr(func, TORNADO_TRACE_ID, None)
            if unique_id:
                epsagon.trace.trace_factory.get_or_create_trace(
                    unique_id=unique_id
                )
        except Exception as instrumentation_exception:  # pylint: disable=W0703
            epsagon.trace.trace_factory.add_exception(
                instrumentation_exception,
                traceback.format_exc()
            )

        return wrapped(*args, **kwargs)

    @classmethod
    def wrap(cls, wrapped, _, args, kwargs):
        """
        Instrument stack context's wrap function
        :param wrapped:
        :param _:
        :param args:
        :param kwargs:
        :return:
        """
        unique_id = epsagon.trace.trace_factory.get_or_create_trace().unique_id
        res = wrapped(*args, **kwargs)
        if res and unique_id:
            setattr(res, TORNADO_TRACE_ID, unique_id)
        return res


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
        'RequestHandler.finish',
        TornadoWrapper.after_request
    )
    wrapt.wrap_function_wrapper(
        'tornado.web',
        'RequestHandler.log_exception',
        TornadoWrapper.collect_exception
    )
    wrapt.wrap_function_wrapper(
        'tornado.ioloop',
        'IOLoop._run_callback',
        TornadoWrapper.run_callback
    )
    wrapt.wrap_function_wrapper(
        'tornado.stack_context',
        'wrap',
        TornadoWrapper.wrap
    )
