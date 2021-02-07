"""
Tornado patcher module.
"""

from __future__ import absolute_import
import time
import traceback
import uuid
from functools import partial
import wrapt
from tornado.httpclient import HTTPRequest
from tornado.httputil import HTTPHeaders
import epsagon.trace
from epsagon.modules.general_wrapper import wrapper
from epsagon.runners.tornado import TornadoRunner
from epsagon.http_filters import ignore_request, is_ignored_endpoint
from epsagon.utils import (
    collect_container_metadata,
    print_debug,
    get_epsagon_http_trace_id
)
from ..constants import EPSAGON_HEADER
from ..events.tornado_client import TornadoClientEventFactory


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
        print_debug('before_request Tornado request')
        try:
            ignored = ignore_request('', instance.request.path)
            if not ignored and not is_ignored_endpoint(instance.request.path):
                unique_id = str(uuid.uuid4())
                trace = epsagon.trace.trace_factory.get_or_create_trace(
                    unique_id=unique_id
                )

                trace.prepare()

                setattr(instance, TORNADO_TRACE_ID, unique_id)

                cls.RUNNERS[unique_id] = (
                    TornadoRunner(time.time(), instance.request)
                )

                trace.set_runner(cls.RUNNERS[unique_id])
                print_debug('Created Tornado Runner')

                # Collect metadata in case this is a container.
                collect_container_metadata(
                    cls.RUNNERS[unique_id].resource['metadata']
                )
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
        print_debug('after_request Tornado request')
        response_body = None
        try:
            response_body = getattr(instance, '_write_buffer', None)
            if response_body and isinstance(response_body, list):
                response_body = b''.join(response_body)
        except Exception as instrumentation_exception:  # pylint: disable=W0703
            epsagon.trace.trace_factory.add_exception(
                instrumentation_exception,
                traceback.format_exc()
            )

        res = wrapped(*args, **kwargs)
        trace = None
        is_trace_sent = False
        try:
            unique_id = getattr(instance, TORNADO_TRACE_ID, None)
            if not unique_id:
                return res

            tornado_runner = cls.RUNNERS.pop(unique_id)

            trace = epsagon.trace.trace_factory.switch_active_trace(
                unique_id
            )

            # Ignoring 404s
            if getattr(instance, '_status_code', None) == 404:
                epsagon.trace.trace_factory.pop_trace(trace=trace)
                print_debug('Ignoring 404 Tornado request')
                return res

            if trace:
                content = (
                    instance._headers.get(  # pylint: disable=protected-access
                        'Content-Type',
                        ''
                    )
                )
                ignored = ignore_request(content, '')
                if not ignored:
                    tornado_runner.update_response(instance, response_body)
                    epsagon.trace.trace_factory.send_traces(trace)
                    is_trace_sent = True
        except Exception:  # pylint: disable=W0703
            if not is_trace_sent and trace:
                epsagon.trace.trace_factory.pop_trace(trace=trace)

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
        print_debug('collect_exception Tornado request')
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
                epsagon.trace.trace_factory.switch_active_trace(unique_id)
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
        res = wrapped(*args, **kwargs)
        if res and not hasattr(res, TORNADO_TRACE_ID):
            trace = epsagon.trace.trace_factory.active_trace
            if trace and trace.unique_id:
                setattr(res, TORNADO_TRACE_ID, trace.unique_id)
        return res

    @classmethod
    def thread_pool_submit(cls, func, _, args, kwargs):
        """
        Submits a new worker to the thread pool, wrapped in our injector
        """
        unique_id = None

        try:
            trace = epsagon.trace.trace_factory.get_trace()
            if trace:
                unique_id = trace.unique_id

        except Exception as instrumentation_exception:  # pylint: disable=W0703
            epsagon.trace.trace_factory.add_exception(
                instrumentation_exception,
                traceback.format_exc()
            )

        fn = args[0]
        fn_args = args[1:]
        return func(cls.thread_pool_execution, unique_id, fn, fn_args, kwargs)

    @classmethod
    def thread_pool_execution(cls, unique_id, fn, args, kwargs):
        """
            Middleware to inject unique id to the thread pool execution
        """
        try:
            if unique_id is not None:
                epsagon.trace.trace_factory.set_thread_local_unique_id(
                    unique_id
                )
        except Exception as instrumentation_exception:  # pylint: disable=W0703
            epsagon.trace.trace_factory.add_exception(
                instrumentation_exception,
                traceback.format_exc()
            )
        res = fn(*args, **kwargs)
        epsagon.trace.trace_factory.unset_thread_local_unique_id()
        return res


def _prepare_http_request(request, raise_error=True, **kwargs):
    """
    Copying parameters from original `AsyncHTTPClient.fetch` function
    :return: HTTPRequest, raise_error bool
    """
    # request can be a URL string or a HTTPRequest object
    if not isinstance(request, HTTPRequest):
        request = HTTPRequest(request, **kwargs)

    return request, raise_error


def _wrapper(wrapped, instance, args, kwargs):
    """
    General wrapper for AsyncHTTPClient instrumentation.
    :param wrapped: wrapt's wrapped
    :param instance: wrapt's instance
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    :return: None
    """
    print_debug('AsyncHTTPClient init')
    try:
        request, raise_error = _prepare_http_request(*args, **kwargs)
    except Exception:  # pylint: disable=W0703
        return wrapped(*args, **kwargs)

    print_debug('AsyncHTTPClient setting header')
    trace_header = get_epsagon_http_trace_id()

    if isinstance(request.headers, HTTPHeaders):
        if not request.headers.get(EPSAGON_HEADER):
            request.headers.add(EPSAGON_HEADER, trace_header)
    elif isinstance(request.headers, dict):
        if EPSAGON_HEADER not in request.headers:
            request.headers[EPSAGON_HEADER] = trace_header

    print_debug('AsyncHTTPClient running wrapper')
    return wrapper(
        TornadoClientEventFactory,
        wrapped,
        instance,
        (request, ),  # new args
        {'raise_error': raise_error}  # new kwargs
    )


def patch():
    """
    Patch module.
    """
    try:
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
            'concurrent.futures',
            'ThreadPoolExecutor.submit',
            TornadoWrapper.thread_pool_submit
        )
        wrapt.wrap_function_wrapper(
            'tornado.stack_context',
            'wrap',
            TornadoWrapper.wrap
        )
    except Exception:  # pylint: disable=broad-except
        # Can happen in different Tornado versions.
        pass

    wrapt.wrap_function_wrapper(
        'tornado.httpclient',
        'AsyncHTTPClient.fetch',
        _wrapper
    )
