"""
Middleware for Python aiohttp.
"""

from __future__ import absolute_import
import time
import warnings
from aiohttp.web import middleware
from aiohttp.web_exceptions import HTTPNotFound

import epsagon.trace
import epsagon.triggers.http
from epsagon.runners.aiohttp import AiohttpRunner
from epsagon.common import EpsagonWarning
from epsagon.utils import (
    collect_container_metadata,
    get_traceback_data_from_exception
)
from ..http_filters import ignore_request
from ..utils import print_debug


@middleware
async def AiohttpMiddleware(request, handler):
    """
    aiohttp middleware to create a runner with event details
    :param request: incoming request data
    :param handler: original handler
    :return: response data from the handler
    """
    print_debug('[aiohttp] started middleware')
    epsagon.trace.trace_factory.switch_to_async_tracer()

    if ignore_request('', request.path.lower()):
        print_debug('[aiohttp] ignoring request')
        return await handler(request)

    trace = epsagon.trace.trace_factory.get_or_create_trace()
    trace.prepare()
    runner = None
    response = None

    try:
        body = await request.text()
        print_debug('[aiohttp] got body')
        runner = AiohttpRunner(time.time(), request, body, handler)
        trace.set_runner(runner)
        collect_container_metadata(runner.resource['metadata'])
        print_debug('[aiohttp] initialized runner')
    except Exception as exception: # pylint: disable=W0703
        warnings.warn('Could not extract request', EpsagonWarning)

    raised_err = None
    try:
        response = await handler(request)
        print_debug('[aiohttp] got response')
    except HTTPNotFound:
        # Ignoring 404s
        epsagon.trace.trace_factory.pop_trace(trace)
        raise
    except Exception as exception:  # pylint: disable=W0703
        raised_err = exception
        traceback_data = get_traceback_data_from_exception(exception)
        trace.runner.set_exception(exception, traceback_data)

    if response is not None and runner:
        if ignore_request(response.content_type.lower(), ''):
            return response

        runner.update_response(response)

    if runner:
        print_debug('[aiohttp] sending trace')
        epsagon.trace.trace_factory.send_traces()
    if raised_err:
        print_debug('[aiohttp] raising error')
        raise raised_err
    print_debug('[aiohttp] middleware done')
    return response
