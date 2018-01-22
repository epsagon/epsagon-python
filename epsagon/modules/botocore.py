"""
botocore patcher module
"""
from __future__ import absolute_import

import wrapt
from botocore.exceptions import ClientError
from epsagon.modules.general_wrapper import wrapper
from ..events.botocore import BotocoreEventFactory


def _botocore_wrapper(wrapped, instance, args, kwargs):
    wrapper(
        BotocoreEventFactory,
        ClientError,
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
        'botocore.client',
        'BaseClient._make_api_call',
        _botocore_wrapper
    )
