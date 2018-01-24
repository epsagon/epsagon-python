"""
pymongo patcher module
"""
from __future__ import absolute_import

import wrapt
from epsagon.modules.general_wrapper import wrapper
from ..events.pymongo import PyMongoEventFactory


def _wrapper(wrapped, instance, args, kwargs):
    return wrapper(
        PyMongoEventFactory,
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
        'pymongo.collection',
        'Collection.insert_one',
        _wrapper
    )
    wrapt.wrap_function_wrapper(
        'pymongo.collection',
        'Collection.insert_many',
        _wrapper
    )
