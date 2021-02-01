"""
Tracing route for Python fastapi.
"""
import time
import json
import json.decoder
import asyncio
from typing import Callable

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

def _switch_tracer_mode(dependant_call):
    """
    Switches the tracer to async/multi threaded mode
    :param dependant_call: the endpoint callback
    :return: True if succeeded, False otherwise
    Fails if dependant_call is None or if trying to switch from different
    tracer modes (async <-> multi threaded)
    """
    if not dependant_call: # shouldn't happen
        return False
    is_coroutine = asyncio.iscoroutinefunction(dependant_call)
    if (
            is_coroutine and
            not epsagon.trace.trace_factory.is_multi_threaded_tracer()
    ):
        epsagon.trace.trace_factory.switch_to_async_tracer()
        return True
    elif not epsagon.trace.trace_factory.is_async_tracer():
        epsagon.trace.trace_factory.switch_to_multiple_traces()
        return True
    return False


class TracingAPIRoute(APIRoute):
    """
    Custom tracing route - traces each route request & response
    """
    def get_route_handler(self) -> Callable:
        """
        Gets a tracing route handler - create a runner with event details,
        including request & response data.
        """
        original_route_handler = super().get_route_handler()
        should_trace = False
        if self.dependant.call is not None:
            should_trace = _switch_tracer_mode(self.dependant.call)
            if not should_trace:
                print_debug(
                    "Cannot trace both FastAPI syncronous and async endpoints"
                )

        async def custom_route_handler(request: Request) -> Response:
            """
            Traces given request and its response.
            :param request: to trace
            """
            should_ignore_request = True
            try:
                if not should_trace:
                    return await original_route_handler(request)
                if not ignore_request('', request.url.path.lower()):
                    should_ignore_request = False
                    trace = epsagon.trace.trace_factory.get_or_create_trace()
                    trace.prepare()

            except Exception as exception: # pylint: disable=W0703
                return await original_route_handler(request)

            if should_ignore_request:
                return await original_route_handler(request)

            runner = None
            response = None
            try:
                runner = FastapiRunner(time.time(), request)
                trace.set_runner(runner)
                collect_container_metadata(runner.resource['metadata'])
            except Exception as exception: # pylint: disable=W0703
                warnings.warn('Could not extract request', EpsagonWarning)
            raised_err = None
            try:
                response: Response = await original_route_handler(request)
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
            try:
                if not raised_err and response is not None and runner:
                    if ignore_request(
                            response.headers.get('Content-Type', '').lower(),
                            ''
                    ):
                        return response

                    runner.update_response(response)

                if runner:
                    epsagon.trace.trace_factory.send_traces()
            except Exception as exception:  # pylint: disable=W0703
                print_debug('Failed to send traces: {}'.format(exception))

            if raised_err:
                raise raised_err

            return response

        return custom_route_handler
