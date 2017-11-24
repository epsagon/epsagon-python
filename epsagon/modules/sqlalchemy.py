"""
sql alchemy patcher module
"""

from __future__ import absolute_import
import wrapt
from ..events.sqlalchemy import SQLAlchemyEventFactory


def _commit_wrapper(wrapped, instance, args, kwargs):
    event = SQLAlchemyEventFactory.factory(wrapped, instance, args)
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
        'sqlalchemy.orm.session',
        'Session.commit',
        _commit_wrapper
    )

    wrapt.wrap_function_wrapper(
        'sqlalchemy.orm.session',
        'Session.query',
        _commit_wrapper
    )
