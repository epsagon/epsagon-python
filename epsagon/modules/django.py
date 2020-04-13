"""
Django patcher module.
"""

from __future__ import absolute_import
import wrapt
from ..utils import print_debug, is_lambda_env

try:
    from django.conf import settings
except ImportError:
    settings = None  # pylint: disable=invalid-name

EPSAGON_MIDDLEWARE = 'epsagon.wrappers.django.DjangoMiddleware'


def _wrapper(wrapped, _instance, args, kwargs):
    """
    Adds `EPSAGON_MIDDLEWARE` into django.conf.settings.
    :param wrapped: wrapt's wrapped
    :param _instance: wrapt's instance
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    """

    # Skip on Lambda environment since it's not relevant and might be duplicate
    if is_lambda_env():
        return wrapped(*args, **kwargs)

    try:
        # Extract middleware engine (varying between Django versions)
        if hasattr(settings, 'MIDDLEWARE') and settings.MIDDLEWARE is not None:
            # Check if not instrumented already
            if EPSAGON_MIDDLEWARE in settings.MIDDLEWARE:
                return wrapped(*args, **kwargs)

            # Add Epsagon's middleware to the list
            if isinstance(settings.MIDDLEWARE, tuple):
                settings.MIDDLEWARE = (
                    (EPSAGON_MIDDLEWARE,) + settings.MIDDLEWARE
                )
            elif isinstance(settings.MIDDLEWARE, list):
                settings.MIDDLEWARE = [EPSAGON_MIDDLEWARE] + settings.MIDDLEWARE
        elif (
            hasattr(settings, 'MIDDLEWARE_CLASSES') and
            settings.MIDDLEWARE_CLASSES is not None
        ):
            # Check if not instrumented already
            if EPSAGON_MIDDLEWARE in settings.MIDDLEWARE_CLASSES:
                return wrapped(*args, **kwargs)

            # Add Epsagon's middleware to the list
            if isinstance(settings.MIDDLEWARE_CLASSES, tuple):
                settings.MIDDLEWARE = (
                    (EPSAGON_MIDDLEWARE,) + settings.MIDDLEWARE_CLASSES
                )
            elif isinstance(settings.MIDDLEWARE_CLASSES, list):
                settings.MIDDLEWARE = (
                    [EPSAGON_MIDDLEWARE] + settings.MIDDLEWARE_CLASSES
                )
    except Exception:  # pylint: disable=broad-except
        print_debug('Could not add Django middleware')
    return wrapped(*args, **kwargs)


def patch():
    """
    Patch module.
    :return: None
    """
    wrapt.wrap_function_wrapper(
        'django.core.handlers.base',
        'BaseHandler.load_middleware',
        _wrapper
    )
