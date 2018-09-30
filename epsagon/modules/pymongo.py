"""
pymongo patcher module.
"""

from __future__ import absolute_import
import wrapt
from epsagon.modules.general_wrapper import wrapper
from ..events.pymongo import PyMongoEventFactory


def _wrapper(wrapped, instance, args, kwargs):
    """
    General wrapper for pymongo instrumentation.
    :param wrapped: wrapt's wrapped
    :param instance: wrapt's instance
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    :return: None
    """

    return wrapper(PyMongoEventFactory, wrapped, instance, args, kwargs)


def patch():
    """
    Patch module.
    :return: None
    """

    wrapt.wrap_function_wrapper(
        'pymongo.collection',
        'Collection.insert_one',
        _wrapper
    )
    wrapt.wrap_function_wrapper(
        'pymongo.collection',
        'Collection.insert_many',
        _wrapper
    )
