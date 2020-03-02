"""
flask patcher module.
"""

from __future__ import absolute_import
import wrapt
from ..wrappers.flask import FlaskWrapper


def _wrapper(wrapped, instance, args, kwargs):
    """
    Adds `FlaskWrapper` into Flask app.
    :param wrapped: wrapt's wrapped
    :param instance: wrapt's instance
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    """
    try:
        response = wrapped(*args, **kwargs)
        FlaskWrapper(instance)
        return response
    except Exception:  # pylint: disable=broad-except
        raise


def patch():
    """
    Patch module.
    :return: None
    """
    wrapt.wrap_function_wrapper('flask', 'Flask.__init__', _wrapper)
