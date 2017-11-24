"""
pymongo patcher module
"""

from __future__ import absolute_import
import wrapt
from ..events.pymongo import PyMongoEvent


def _wrapper(wrapped, instance, args, kwargs):
    event = PyMongoEvent(instance, args)
    try:
        response = wrapped(*args, **kwargs)
        event.post_update(response)
        return response
    except Exception as exception:
        raise exception
    finally:
        event.add_event()


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
