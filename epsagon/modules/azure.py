"""
Azure sdk patcher module.
"""

from __future__ import absolute_import
import wrapt
from epsagon.modules.general_wrapper import wrapper
from ..events.azure import AzureEventFactory


def _wrapper(wrapped, instance, args, kwargs):
    """
    General wrapper for Azure sdk instrumentation.
    :param wrapped: wrapt's wrapped
    :param instance: wrapt's instance
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    :return: None
    """
    return wrapper(AzureEventFactory, wrapped, instance, args, kwargs)


def patch():
    """
    Patch module.
    :return: None
    """
    wrapt.wrap_function_wrapper(
        'azure.cosmos.container',
        'ContainerProxy.delete_item',
        _wrapper
    )
    wrapt.wrap_function_wrapper(
        'azure.cosmos.container',
        'ContainerProxy.upsert_item',
        _wrapper
    )
    wrapt.wrap_function_wrapper(
        'azure.cosmos.container',
        'ContainerProxy.query_items',
        _wrapper
    )
