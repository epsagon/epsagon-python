"""
Tracing route for Python fastapi.
"""
import time
import uuid
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
from epsagon.constants import EPSAGON_MARKER
from epsagon.utils import (
    collect_container_metadata,
    get_traceback_data_from_exception
)
from ..http_filters import ignore_request
from ..utils import is_lambda_env, print_debug

DEFAULT_SUCCESS_STATUS_CODE = 200
DEFAULT_ERROR_STATUS_CODE = 500
EPSAGON_REQUEST_PARAM_NAME = 'epsagon_request'
SCOPE_UNIQUE_ID = 'trace_unique_id'
SCOPE_CONTAINER_METADATA_COLLECTED = 'container_metadata'
SCOPE_IGNORE_REQUEST = 'ignore_request'

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


def _handle_response(epsagon_scope, response, status_code, trace, raised_err):
    """
    Handles the HTTP handler response.
    :param epsagon_scope:
    :param response:
    :param status_code:
    :param trace: to update the response with
    :param raised_err: any error which might occured while trying to get
    the response.
    :return: the response, raising raised_err if its not None.
    """
    try:
        if raised_err:
            status_code = DEFAULT_ERROR_STATUS_CODE
        elif isinstance(response, Response):
            if ignore_request(
                    response.headers.get('Content-Type', '').lower(),
                    ''
            ):
                epsagon_scope[SCOPE_IGNORE_REQUEST] = True
                return response

        if response is not None:
            trace.runner.update_response(response, status_code=status_code)

    except Exception as exception:  # pylint: disable=W0703
        print_debug('Failed to handle response: {}'.format(exception))

    if raised_err:
        raise raised_err

    return response


def _get_epsagon_scope_data(request: Request) -> str:
    """
    Gets the epsagon scope data from a given request.
    Returns None if not found.
    """
    try:
        if not request.scope:
            return None
        return request.scope.get(EPSAGON_MARKER)
    except Exception: # pylint: disable=broad-except
        return None


def _extract_request_body(trace, request):
    """
    Extracts the request body (if exists), and saves it to the trace runner.
    """
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
        if loop:
            loop.close()


# pylint: disable=too-many-return-statements
def _fastapi_handler(
        original_handler,
        request,
        status_code,
        args,
        kwargs
):
    """
    FastAPI generic handler - for callbacks executed by a threadpool
    :param original_handler: the wrapped original handler
    :param request: the given handler request
    :param status_code: the default configured response status code.
    Can be None when called by exception handlers wrapper, as there's
    no status code configuration for exception handlers.
    """
    epsagon_scope = _get_epsagon_scope_data(request)
    if not epsagon_scope:
        return original_handler(*args, **kwargs)
    unique_id = epsagon_scope.get(SCOPE_UNIQUE_ID)
    if not unique_id or epsagon_scope.get(SCOPE_IGNORE_REQUEST):
        return original_handler(*args, **kwargs)

    try:
        epsagon.trace.trace_factory.set_thread_local_unique_id(
            unique_id=unique_id
        )
    except Exception: # pylint: disable=broad-except
        return original_handler(*args, **kwargs)

    trace = None
    should_ignore_request = True
    try:
        if not ignore_request('', request.url.path.lower()):
            should_ignore_request = False
            trace = epsagon.trace.trace_factory.get_trace()
        else:
            epsagon_scope[SCOPE_IGNORE_REQUEST] = True

    except Exception as exception: # pylint: disable=W0703
        return original_handler(*args, **kwargs)

    if not trace or should_ignore_request:
        return original_handler(*args, **kwargs)

    created_runner = False
    response = None
    if not trace.runner:
        try:
            trace.set_runner(FastapiRunner(time.time(), request))
            created_runner = True
        except Exception as exception: # pylint: disable=W0703
            print_debug('Failed to add FastAPI runner event, skipping trace')
            # failed to add runner event, skipping trace
            return original_handler(*args, **kwargs)
    try:
        if not epsagon_scope.get(SCOPE_CONTAINER_METADATA_COLLECTED):
            collect_container_metadata(trace.runner.resource['metadata'])
            epsagon_scope[SCOPE_CONTAINER_METADATA_COLLECTED] = True
    except Exception as exception: # pylint: disable=W0703
        warnings.warn(
            'Could not extract container metadata',
            EpsagonWarning
        )
    raised_err = None
    try:
        response = original_handler(*args, **kwargs)
    except Exception as exception:  # pylint: disable=W0703
        raised_err = exception
    finally:
        try:
            epsagon.trace.trace_factory.unset_thread_local_unique_id()
        except Exception: # pylint: disable=broad-except
            pass
    # no need to update request body if runner already created before
    if created_runner:
        _extract_request_body(trace, request)

    return _handle_response(
        epsagon_scope,
        response,
        status_code,
        trace,
        raised_err
    )


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
        return _fastapi_handler(
            original_handler, request, status_code, args, kwargs
        )

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
            _wrap_handler(
                self.dependant,
                kwargs.pop('status_code', DEFAULT_SUCCESS_STATUS_CODE)
            )


def exception_handler_wrapper(original_handler):
    """
    Wraps an exception handler
    """
    is_async = asyncio.iscoroutinefunction(original_handler)
    if is_async:
        # async handlers are not supported
        return original_handler

    def wrapped_handler(*args, **kwargs):
        if not args or len(args) != 2:
            return original_handler(*args, **kwargs)
        request: Request = args[0]
        return _fastapi_handler(
            original_handler, request, None, args, kwargs
        )

    return wrapped_handler


def _clean_trace(trace):
    """ Cleans the given trace """
    if trace:
        try:
            epsagon.trace.trace_factory.pop_trace(trace=trace)
        except Exception: # pylint: disable=broad-except
            pass


async def server_call_wrapper(wrapped, _instance, args, kwargs):
    """
    Wraps the main fastapi server request entrypoint - which is
    the ServerErrorMiddleware __call_ function.
    :param wrapped: wrapt's wrapped
    :param instance: wrapt's instance
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    """
    # Skip on Lambda environment since it's not relevant and might be duplicate
    if is_lambda_env() or not args or len(args) != 3:
        return await wrapped(*args, **kwargs)

    scope = args[0]
    if not scope or scope.get('type', '') != 'http':
        return await wrapped(*args, **kwargs)

    trace = None
    try:
        epsagon.trace.trace_factory.switch_to_multiple_traces()
        unique_id = str(uuid.uuid4())
        trace = epsagon.trace.trace_factory.get_or_create_trace(
            unique_id=unique_id
        )
        trace.prepare()
        scope[EPSAGON_MARKER] = {
            SCOPE_UNIQUE_ID: unique_id,
        }
    except Exception: # pylint: disable=broad-except
        _clean_trace(trace)
        return await wrapped(*args, **kwargs)

    response = None
    raised_error = None
    sent_trace = False
    epsagon_scope = scope[EPSAGON_MARKER]
    try:
        response = await wrapped(*args, **kwargs)
    except Exception as exception: # pylint: disable=broad-except
        raised_error = exception

    if trace.runner and not epsagon_scope.get(SCOPE_IGNORE_REQUEST):
        try:
            if raised_error:
                traceback_data = get_traceback_data_from_exception(raised_error)
                trace.runner.set_exception(raised_error, traceback_data)
                trace.runner.update_status_code(
                    DEFAULT_ERROR_STATUS_CODE,
                    override=False
                )
            epsagon.trace.trace_factory.send_traces(trace=trace)
            sent_trace = True
        except Exception as exception: # pylint: disable=broad-except
            print_debug('Failed to send traces: {}'.format(exception))

    scope.pop(EPSAGON_MARKER, None)
    if not sent_trace:
        _clean_trace(trace)
    if raised_error:
        raise raised_error from None
    return response
