"""
pymongo patcher module
"""

from __future__ import absolute_import
import wrapt
from ..events.pymongo import PyMongoEventFactory


def _wrapper(wrapped, instance, args, kwargs):
    response = None
    exception = None
    try:
        response = wrapped(*args, **kwargs)
        return response
    except Exception as exception:
        raise exception
    finally:
        PyMongoEventFactory.create_event(wrapped, instance, args, kwargs, response, exception)


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
