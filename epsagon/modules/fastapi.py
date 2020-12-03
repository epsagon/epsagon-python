"""
fastapi patcher module.
"""

from __future__ import absolute_import
import wrapt
from fastapi.routing import APIRoute
from ..wrappers.fastapi import TracingRoute
from ..utils import is_lambda_env

def _wrapper(wrapped, instance, args, kwargs):
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
    route_class = kwargs.get("route_class", APIRoute)
    if route_class != APIRoute:
        return wrapped(*args, **kwargs)
    kwargs["route_class"] = TracingRoute
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
