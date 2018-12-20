"""
Epsagon's init.
"""

from __future__ import absolute_import
import os
from .utils import init
from .patcher import patch_all
from .constants import __version__
from .trace import tracer


def dummy_wrapper(func):
    """
    A dummy wrapper for when Epsagon is disabled
    :param func: The function to wrap
    :return: The same function, unchanged
    """
    return func


if os.environ.get('DISABLE_EPSAGON') == 'TRUE':
    os.environ['DISABLE_EPSAGON_PATCH'] = 'TRUE'
    lambda_wrapper = dummy_wrapper  # pylint: disable=C0103
    step_lambda_wrapper = dummy_wrapper  # pylint: disable=C0103
    azure_wrapper = dummy_wrapper  # pylint: disable=C0103
    python_wrapper = dummy_wrapper  # pylint: disable=C0103
    EpsagonFlask = dummy_wrapper  # pylint: disable=C0103
else:
    # Environments.
    from .wrappers import (
        lambda_wrapper,
        step_lambda_wrapper,
        azure_wrapper,
        python_wrapper
    )

    # Frameworks.
    try:
        from .wrappers.flask import FlaskWrapper as flask_wrapper
    except ImportError:
        flask_wrapper = dummy_wrapper


# pylint: disable=C0103
label = tracer.add_label

__all__ = ['lambda_wrapper', 'azure_wrapper', 'python_wrapper', 'init',
           'step_lambda_wrapper', 'flask_wrapper']


# The modules are patched only if DISABLE_EPSAGON_PATCH variable is NOT 'TRUE'
if os.environ.get('DISABLE_EPSAGON_PATCH') != 'TRUE':
    patch_all()
