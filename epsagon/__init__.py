"""
Epsagon's init.
"""

from __future__ import absolute_import
import os
from .utils import init, print_debug
from .patcher import patch_all
from .constants import __version__, EPSAGON_HANDLER
from .trace import trace_factory

if os.getenv(EPSAGON_HANDLER):
    from .handler import wrapper


def auto_load(_):
    """
    Called when setting `AUTOWRAPT_BOOTSTRAP=epsagon` (auto-tracing).
    """
    print_debug('Initialized using auto-tracing')
    init()


def dummy_wrapper(func):
    """
    A dummy wrapper for when Epsagon is disabled
    :param func: The function to wrap
    :return: The same function, unchanged
    """
    return func


if os.getenv('DISABLE_EPSAGON') == 'TRUE':
    os.environ['DISABLE_EPSAGON_PATCH'] = 'TRUE'
    lambda_wrapper = dummy_wrapper  # pylint: disable=C0103
    step_lambda_wrapper = dummy_wrapper  # pylint: disable=C0103
    chalice_wrapper = dummy_wrapper  # pylint: disable=C0103
    azure_wrapper = dummy_wrapper  # pylint: disable=C0103
    python_wrapper = dummy_wrapper  # pylint: disable=C0103
    flask_wrapper = dummy_wrapper  # pylint: disable=C0103
    gcp_wrapper = dummy_wrapper  # pylint: disable=C0103
else:
    # Environments.
    from .wrappers import (
        lambda_wrapper,
        step_lambda_wrapper,
        chalice_wrapper,
        azure_wrapper,
        python_wrapper,
        gcp_wrapper
    )

    # Frameworks.
    try:
        from .wrappers.flask import FlaskWrapper as flask_wrapper
    except ImportError:
        flask_wrapper = dummy_wrapper


# pylint: disable=C0103
label = trace_factory.add_label
error = trace_factory.set_error
disable = trace_factory.disable
enable = trace_factory.enable


__all__ = [
    'lambda_wrapper',
    'azure_wrapper',
    'python_wrapper',
    'init',
    'step_lambda_wrapper',
    'flask_wrapper',
    'wrapper',
    'gcp_wrapper',
    'chalice_wrapper',
    'auto_load',
]


# The modules are patched only if DISABLE_EPSAGON_PATCH variable is NOT 'TRUE'
if os.getenv('DISABLE_EPSAGON_PATCH') != 'TRUE':
    patch_all()
