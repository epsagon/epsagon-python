"""
fastapi patcher module.
"""

from __future__ import absolute_import
import wrapt
from fastapi.routing import APIRoute
from ..wrappers.fastapi import (
    TracingAPIRoute,
    exception_handler_wrapper,
    server_call_wrapper,
)
from ..utils import is_lambda_env, print_debug

def _wrapper(wrapped, _instance, args, kwargs):
    """
    Adds TracingRoute into APIRouter (FastAPI).
    :param wrapped: wrapt's wrapped
    :param instance: wrapt's instance
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    """

    # Skip on Lambda environment since it's not relevant and might be duplicate
    if is_lambda_env():
        return wrapped(*args, **kwargs)
    route_class = kwargs.get('route_class', APIRoute)
    if route_class != APIRoute:
        # custom routes are not supported
        print_debug(
            f'Custom FastAPI route {route_class.__name__} is not supported'
        )
        return wrapped(*args, **kwargs)
    kwargs['route_class'] = TracingAPIRoute
    return wrapped(*args, **kwargs)

def _exception_handler_wrapper(wrapped, _instance, args, kwargs):
    """
    Wraps the handler given to add_exception_handler.
    :param wrapped: wrapt's wrapped
    :param instance: wrapt's instance
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    """
    # Skip on Lambda environment since it's not relevant and might be duplicate
    if is_lambda_env():
        return wrapped(*args, **kwargs)

    if args and len(args) == 2:
        args = list(args)
        args[1] = exception_handler_wrapper(args[1])
    return wrapped(*args, **kwargs)


def patch():
    """
    Patch module.
    :return: None
    """
    wrapt.wrap_function_wrapper(
        'fastapi',
        'APIRouter.__init__',
        _wrapper
    )
    wrapt.wrap_function_wrapper(
        'starlette.applications',
        'Starlette.add_exception_handler',
        _exception_handler_wrapper
    )
    wrapt.wrap_function_wrapper(
        'starlette.middleware.errors',
        'ServerErrorMiddleware.__call__',
        server_call_wrapper
    )
