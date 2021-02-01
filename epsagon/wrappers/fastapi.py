"""
Tracing route for Python fastapi.
"""
import time
import json
import json.decoder
import asyncio

import warnings
from fastapi.routing import APIRoute
from fastapi import Request, Response
from starlette.requests import ClientDisconnect

import epsagon.trace
from epsagon.runners.fastapi import FastapiRunner
from epsagon.common import EpsagonWarning
from epsagon.utils import (
    collect_container_metadata,
    get_traceback_data_from_exception
)
from ..http_filters import ignore_request
from ..utils import print_debug

EPSAGON_REQUEST_PARAM_NAME = 'epsagon_request'

def _switch_tracer_mode(is_coroutine):
    """
    Switches the tracer to async/multi threaded mode
    :param is_coroutine: indicates whether the endpoint is a coroutine
    :return: True if succeeded, False otherwise
    Fails if handler is None or if trying to switch from different
    tracer modes (async <-> multi threaded)
    """
    if (
            is_coroutine and
            not epsagon.trace.trace_factory.is_multi_threaded_tracer()
    ):
        epsagon.trace.trace_factory.switch_to_async_tracer()
        return True
    if not epsagon.trace.trace_factory.is_async_tracer():
        epsagon.trace.trace_factory.switch_to_multiple_traces()
        return True
    return False


def _handle_wrapper_params(_args, kwargs, original_request_param_name):
    """
    Handles the sync/async given parameters.
    Getting the request object injected by Epsagon. If the user set the
    If the original handler is set to get the Request object, then injecting
    it back to kwargs with its original param name.
    :return: the request object, None if not exists
    """
    if EPSAGON_REQUEST_PARAM_NAME not in kwargs:
        return None
    request = kwargs.pop(EPSAGON_REQUEST_PARAM_NAME)
    if original_request_param_name:
        kwargs[original_request_param_name] = request
    return request


def _handle_response(response, trace, raised_err):
    """
    Handles the HTTP handler response. Used by both async & sync wrappers.
    :param response:
    :param trace: to update the response with
    :param raised_err: any error which might occured while trying to get
    the response.
    :return: the response, raising raised_err if its not None.
    """
    try:
        if not raised_err and response is not None:
            if ignore_request(
                    response.headers.get('Content-Type', '').lower(),
                    ''
            ):
                epsagon.trace.trace_factory.pop_trace(trace=trace)
                return response

        if response is not None:
            trace.runner.update_response(response)
        epsagon.trace.trace_factory.send_traces()
    except Exception as exception:  # pylint: disable=W0703
        print_debug('Failed to send traces: {}'.format(exception))
        epsagon.trace.trace_factory.pop_trace(trace=trace)

    if raised_err:
        raise raised_err

    return response

# pylint: disable=too-many-statements
def _wrap_handler(dependant):
    """
    Wraps the endppint handler.
    """
    original_handler = dependant.call
    original_request_param_name = dependant.request_param_name
    is_async = asyncio.iscoroutinefunction(original_handler)
    dependant.request_param_name = EPSAGON_REQUEST_PARAM_NAME
    def sync_wrapped_handler(*args, **kwargs):
        """
        Synchronous wrapper handler
        """
        request: Request = _handle_wrapper_params(
            args, kwargs, original_request_param_name
        )
        if not request or not _switch_tracer_mode(is_async):
            return original_handler(*args, **kwargs)
        should_ignore_request = True
        try:
            if not ignore_request('', request.url.path.lower()):
                should_ignore_request = False
                trace = epsagon.trace.trace_factory.get_or_create_trace()
                trace.prepare()

        except Exception as exception: # pylint: disable=W0703
            return original_handler(*args, **kwargs)

        if should_ignore_request:
            return original_handler(*args, **kwargs)

        runner = None
        response = None
        try:
            runner = FastapiRunner(time.time(), request)
            trace.set_runner(runner)
        except Exception as exception: # pylint: disable=W0703
            print_debug('Failed to add FastAPI runner event, skipping trace')
            # failed to add runner event, skipping trace
            epsagon.trace.trace_factory.pop_trace(trace=trace)
            return original_handler(*args, **kwargs)
        try:
            collect_container_metadata(runner.resource['metadata'])
        except Exception as exception: # pylint: disable=W0703
            warnings.warn(
                'Could not extract container metadata',
                EpsagonWarning
            )
        raised_err = None
        try:
            response: Response = original_handler(*args, **kwargs)
        except Exception as exception:  # pylint: disable=W0703
            raised_err = exception
            traceback_data = get_traceback_data_from_exception(exception)
            trace.runner.set_exception(exception, traceback_data)
        try:
            loop = asyncio.new_event_loop()
            trace.runner.update_request_body(
                json.dumps(loop.run_until_complete(request.json()))
            )

        except json.decoder.JSONDecodeError:
            print_debug('Could not JSON-decode request body')
        except ClientDisconnect:
            print_debug(
                'Could not extract request body - client is disconnected'
            )
        except Exception as exception: # pylint: disable=W0703
            print_debug(
                'Could not extract request body: {}'.format(exception)
            )
        finally:
            loop.close()
        return _handle_response(response, trace, raised_err)

    async def async_wrapped_handler(*args, **kwargs):
        """
        Asynchronous wrapper handler
        """
        request = _handle_wrapper_params(
            args, kwargs, original_request_param_name
        )
        if not request or not _switch_tracer_mode(is_async):
            return await original_handler(*args, **kwargs)

        should_ignore_request = True
        try:
            if not ignore_request('', request.url.path.lower()):
                should_ignore_request = False
                trace = epsagon.trace.trace_factory.get_or_create_trace()
                trace.prepare()

        except Exception as exception: # pylint: disable=W0703
            return await original_handler(*args, **kwargs)

        if should_ignore_request:
            return await original_handler(*args, **kwargs)

        runner = None
        response = None
        try:
            runner = FastapiRunner(time.time(), request)
            trace.set_runner(runner)
        except Exception as exception: # pylint: disable=W0703
            print_debug('Failed to add FastAPI runner event, skipping trace')
            # failed to add runner event, skipping trace
            epsagon.trace.trace_factory.pop_trace(trace=trace)
            return await original_handler(*args, **kwargs)
        try:
            collect_container_metadata(runner.resource['metadata'])
        except Exception as exception: # pylint: disable=W0703
            warnings.warn(
                'Could not extract container metadata',
                EpsagonWarning
            )
        raised_err = None
        try:
            response = await original_handler(*args, **kwargs)
        except Exception as exception:  # pylint: disable=W0703
            raised_err = exception
            traceback_data = get_traceback_data_from_exception(exception)
            trace.runner.set_exception(exception, traceback_data)
        try:
            trace.runner.update_request_body(
                json.dumps(await request.json())
            )
        except json.decoder.JSONDecodeError:
            print_debug('Could not JSON-decode request body')
        except ClientDisconnect:
            print_debug(
                'Could not extract request body - client is disconnected'
            )
        except Exception as exception: # pylint: disable=W0703
            print_debug(
                'Could not extract request body: {}'.format(exception)
            )
        return _handle_response(response, trace, raised_err)

    if is_async:
        dependant.call = async_wrapped_handler
    else:
        dependant.call = sync_wrapped_handler


class TracingAPIRoute(APIRoute):
    """
    Custom tracing route - traces each route request & response
    """

    def __init__(self, *args, **kwargs):
        """
        wraps the route endpoint with Epsagon wrapper
        """
        super().__init__(*args, **kwargs)
        if self.dependant and self.dependant.call:
            _wrap_handler(self.dependant)
