"""
fastapi patcher module.
"""

from __future__ import absolute_import
import wrapt
from ..wrappers.fastapi import (
    exception_handler_wrapper,
    server_call_wrapper,
    route_class_wrapper,
)
from ..utils import is_lambda_env


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
        'fastapi.routing',
        'APIRoute.__init__',
        route_class_wrapper
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
