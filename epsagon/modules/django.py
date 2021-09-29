"""
Django patcher module.
"""

from __future__ import absolute_import
import traceback
import wrapt
from ..utils import print_debug, is_lambda_env
from ..trace import trace_factory
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


def gunicorn_sync_wrapper(wrapped, _instance, args, kwargs):
    """
    Wraps the gunicorn sync worker handle request.
    Catches request handling errors and finally sending the trace.
    :param wrapped: wrapt's wrapped
    :param _instance: wrapt's instance
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    """

    # Skip on Lambda environment since it's not relevant and might be duplicate
    # also skip if given invalid number of arguments
    if is_lambda_env() or not args or len(args) != 4:
        return wrapped(*args, **kwargs)

    try:
        # creates the trace on the current thread
        trace_factory.switch_to_multiple_traces()
        trace_factory.get_or_create_trace()
    except Exception as error: # pylint: disable=broad-except
        pass
    try:
        return wrapped(*args, **kwargs)
    except StopIteration:
        raise
    except Exception as error: # pylint: disable=broad-except
        trace_factory.set_error(error, traceback.format_exc())
        raise error
    finally:
        try:
            trace_factory.send_traces()
        except Exception: # pylint: disable=broad-except
            trace_factory.pop_trace()


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
    try:
        wrapt.wrap_function_wrapper(
            'gunicorn.workers.ggevent',
            'GeventWorker.handle_request',
            gunicorn_sync_wrapper
        )
        wrapt.wrap_function_wrapper(
            'gunicorn.workers.sync',
            'SyncWorker.handle_request',
            gunicorn_sync_wrapper
        )
    except Exception: # pylint: disable=broad-except
        pass
