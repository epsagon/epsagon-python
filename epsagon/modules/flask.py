"""
flask patcher module.
"""

from __future__ import absolute_import
import wrapt
from ..wrappers.flask import FlaskWrapper
from ..utils import print_debug, is_lambda_env


def _wrapper(wrapped, instance, args, kwargs):
    """
    Adds `FlaskWrapper` into Flask app.
    :param wrapped: wrapt's wrapped
    :param instance: wrapt's instance
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    """
    # Skip on Lambda environment since it's not relevant and might be duplicate
    if is_lambda_env():
        return wrapped(*args, **kwargs)

    response = wrapped(*args, **kwargs)
    try:
        FlaskWrapper(instance)
    except Exception:  # pylint: disable=broad-except
        print_debug('Could not add Flask wrapper')
    return response


def patch():
    """
    Patch module.
    :return: None
    """
    wrapt.wrap_function_wrapper('flask', 'Flask.__init__', _wrapper)
