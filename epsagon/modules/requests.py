"""
requests patcher module
"""
from __future__ import absolute_import

import wrapt
from epsagon.modules.general_wrapper import wrapper
from ..events.requests import RequestsEventFactory


def _request_wrapper(wrapped, instance, args, kwargs):
    wrapper(
        RequestsEventFactory,
        Exception,
        wrapped,
        instance,
        args,
        kwargs
    )


def patch():
    """
    patch module
    :return: None
    """
    wrapt.wrap_function_wrapper(
        'requests',
        'Session.send',
        _request_wrapper
    )
