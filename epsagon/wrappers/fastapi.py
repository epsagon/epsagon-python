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


def _handle_wrapper_params(_args, kwargs, original_request_param_name):
    """
    Handles the sync/async given parameters - gets the request object
    If original handler is set to get the Request object, then getting the
    request using this param. Otherwise, trying to get the Request object using
    Epsagon injected param (and removing this injected param)
    :return: the request object, None if not exists
    """
    if original_request_param_name and original_request_param_name in kwargs:
        return kwargs[original_request_param_name]
    return kwargs.pop(EPSAGON_REQUEST_PARAM_NAME, None)


def _handle_response(response, status_code, trace, raised_err):
    """
    Handles the HTTP handler response.
    :param response:
    :param status_code:
    :param trace: to update the response with
    :param raised_err: any error which might occured while trying to get
    the response.
    :return: the response, raising raised_err if its not None.
    """
    try:
        if not raised_err and isinstance(response, Response):
            if ignore_request(
                    response.headers.get('Content-Type', '').lower(),
                    ''
            ):
                epsagon.trace.trace_factory.pop_trace(trace=trace)
                return response

        if response is not None:
            trace.runner.update_response(response, status_code=status_code)
        epsagon.trace.trace_factory.send_traces()
    except Exception as exception:  # pylint: disable=W0703
        print_debug('Failed to send traces: {}'.format(exception))
        epsagon.trace.trace_factory.pop_trace(trace=trace)

    if raised_err:
        raise raised_err

    return response

# pylint: disable=too-many-statements
def _wrap_handler(dependant, status_code):
    """
    Wraps the endppint handler.
    """
    original_handler = dependant.call
    is_async = asyncio.iscoroutinefunction(original_handler)
    if is_async:
        # async endpoints are not supported
        return

    original_request_param_name = dependant.request_param_name
    if not original_request_param_name:
        dependant.request_param_name = EPSAGON_REQUEST_PARAM_NAME

    def wrapped_handler(*args, **kwargs):
        """
        Synchronous wrapper handler
        """
        request: Request = _handle_wrapper_params(
            args, kwargs, original_request_param_name
        )
        if not request:
            return original_handler(*args, **kwargs)
        epsagon.trace.trace_factory.switch_to_multiple_traces()
        trace = None
        should_ignore_request = True
        try:
            if not ignore_request('', request.url.path.lower()):
                should_ignore_request = False
                trace = epsagon.trace.trace_factory.get_or_create_trace()
                trace.prepare()

        except Exception as exception: # pylint: disable=W0703
            if trace:
                epsagon.trace.trace_factory.pop_trace(trace=trace)
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
            pass
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
        return _handle_response(response, status_code, trace, raised_err)

    dependant.call = wrapped_handler


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
            _wrap_handler(self.dependant, kwargs.pop('status_code', 200))
