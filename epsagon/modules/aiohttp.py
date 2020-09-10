"""
aiohttp patcher module.
"""

from __future__ import absolute_import
import wrapt
from ..wrappers.aiohttp import AiohttpMiddleware
from ..utils import print_debug, is_lambda_env


def _wrapper(wrapped, _instance, args, kwargs):
    """
    Adds `AiohttpMiddleware` into aiohttp app.
    :param wrapped: wrapt's wrapped
    :param _instance: wrapt's instance
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    """
    # Skip on Lambda environment since it's not relevant and might be duplicate
    if is_lambda_env():
        return wrapped(*args, **kwargs)

    try:
        if 'middlewares' not in kwargs:
            kwargs['middlewares'] = []
        kwargs['middlewares'].insert(0, AiohttpMiddleware)
    except Exception:  # pylint: disable=broad-except
        print_debug('Could not add aiohttp wrapper')

    return wrapped(*args, **kwargs)


def patch():
    """
    Patch module.
    :return: None
    """
    wrapt.wrap_function_wrapper(
        'aiohttp.web',
        'Application.__init__',
        _wrapper
    )
