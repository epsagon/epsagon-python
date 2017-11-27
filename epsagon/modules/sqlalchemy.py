"""
sqlalchemy patcher module
"""

from __future__ import absolute_import
import wrapt
from ..events.sqlalchemy import SQLAlchemyEventFactory


def _commit_wrapper(wrapped, instance, args, kwargs):
    response = None
    exception = None
    try:
        response = wrapped(*args, **kwargs)
        return response
    except Exception as exception:
        raise exception
    finally:
        SQLAlchemyEventFactory.create_event(wrapped, instance, args, kwargs, response, exception)


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
