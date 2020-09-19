"""
Middleware for Python aiohttp.
"""

from __future__ import absolute_import
import time
import warnings
from aiohttp.web import middleware

import epsagon.trace
import epsagon.triggers.http
from epsagon.runners.aiohttp import AiohttpRunner
from epsagon.common import EpsagonWarning
from epsagon.utils import (
    collect_container_metadata,
    get_traceback_data_from_exception
)
from ..http_filters import ignore_request


@middleware
async def AiohttpMiddleware(request, handler):
    """
    aiohttp middleware to create a runner with event details
    :param request: incoming request data
    :param handler: original handler
    :return: response data from the handler
    """
    epsagon.trace.trace_factory.switch_to_async_tracer()

    if ignore_request('', request.path.lower()):
        return await handler(request)

    trace = epsagon.trace.trace_factory.get_or_create_trace()
    trace.prepare()
    runner = None
    response = None

    try:
        body = await request.text()
        runner = AiohttpRunner(time.time(), request, body, handler)
        trace.set_runner(runner)
        collect_container_metadata(runner.resource['metadata'])
    except Exception as exception: # pylint: disable=W0703
        warnings.warn('Could not extract request', EpsagonWarning)

    try:
        response = await handler(request)
    except Exception as exception:  # pylint: disable=W0703
        traceback_data = get_traceback_data_from_exception(exception)
        trace.runner.set_exception(exception, traceback_data)

    if response is not None and runner:
        if ignore_request(response.content_type.lower(), ''):
            return response

        runner.update_response(response)

    if runner:
        epsagon.trace.trace_factory.send_traces()

    return response
