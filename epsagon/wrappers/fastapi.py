"""
Middleware for Python fastapi.
"""
import time
import json
import json.decoder
import warnings
import epsagon.trace
#import epsagon.triggers.http
from epsagon.runners.fastapi import FastapiRunner
from epsagon.common import EpsagonWarning
from starlette.middleware.base import BaseHTTPMiddleware
from epsagon.utils import (
    collect_container_metadata,
    get_traceback_data_from_exception
)
from ..http_filters import ignore_request

class FastapiMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        print("here")

        epsagon.trace.trace_factory.switch_to_async_tracer()


        if ignore_request('', request.url.path.lower()):
            return await handler(request)

        trace = epsagon.trace.trace_factory.get_or_create_trace()
        trace.prepare()
        runner = None
        response = None

        try:
            #import ipdb
            #ipdb.set_trace()
            try:
                body = await request.json()
            except json.decoder.JSONDecodeError:
                body = None
            runner = FastapiRunner(time.time(), request, json.dumps(body))
            trace.set_runner(runner)
            collect_container_metadata(runner.resource['metadata'])
        except Exception as exception: # pylint: disable=W0703
            from traceback import print_exc
            print_exc()
            warnings.warn('Could not extract request', EpsagonWarning)

        try:
            response = await call_next(request)
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
        #response = await call_next(request)
        #response.headers['Custom'] = 'Example'
        #return response
