"""
Middleware for Python fastapi.
"""
import time
import json
import json.decoder
from typing import Callable

import warnings
from fastapi.routing import APIRoute
from fastapi import APIRouter, Request, Response

import epsagon.trace
from epsagon.runners.fastapi import FastapiRunner
from epsagon.common import EpsagonWarning
from epsagon.utils import (
    collect_container_metadata,
    get_traceback_data_from_exception
)
from ..http_filters import ignore_request


class TracingRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()
        async def custom_route_handler(request: Request) -> Response:
            epsagon.trace.trace_factory.switch_to_async_tracer()

            if ignore_request('', request.url.path.lower()):
                return await original_route_handler(request)
            trace = epsagon.trace.trace_factory.get_or_create_trace()
            trace.prepare()
            runner = None
            response = None
            try:
                body = await request.json()
            except json.decoder.JSONDecodeError:
                body = None
            try:
                runner = FastapiRunner(time.time(), request, json.dumps(body))
                trace.set_runner(runner)
                collect_container_metadata(runner.resource['metadata'])
            except Exception as exception: # pylint: disable=W0703
                warnings.warn('Could not extract request', EpsagonWarning)

            try:
                response: Response = await original_route_handler(request)
            except Exception as exception:  # pylint: disable=W0703
                traceback_data = get_traceback_data_from_exception(exception)
                trace.runner.set_exception(exception, traceback_data)

            if response is not None and runner:
                if ignore_request(response.headers.get('Content-Type', '').lower(), ''):
                    return response

                runner.update_response(response)

            if runner:
                epsagon.trace.trace_factory.send_traces()

            return response

        return custom_route_handler
