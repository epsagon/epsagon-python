"""
aiohttp patcher module.
"""

from __future__ import absolute_import
import wrapt
from ..wrappers.fastapi import FastapiMiddleware
from ..utils import print_debug, is_lambda_env

def _wrapper(wrapped, instance, args, kwargs):
    """
    Adds `FastapiMiddleware` into FastAPI app.
    :param wrapped: wrapt's wrapped
    :param instance: wrapt's instance
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    """
    response = wrapped(*args, **kwargs)
    # Skip on Lambda environment since it's not relevant and might be duplicate
    if is_lambda_env():
        return response
    try:
        instance.add_middleware(FastapiMiddleware)
    except Exception:  # pylint: disable=broad-except
        print("1")
        print_debug('Could not add fastapi wrapper')

    return response


def patch():
    """
    Patch module.
    :return: None
    """
    wrapt.wrap_function_wrapper(
        'fastapi',
        'FastAPI.__init__',
        _wrapper
    )
