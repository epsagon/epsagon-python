"""
sqlalchemy patcher module
"""

from __future__ import absolute_import

import traceback

import wrapt

from epsagon.trace import tracer
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
        try:
            SQLAlchemyEventFactory.create_event(
                wrapped,
                instance,
                args,
                kwargs,
                response,
                exception
            )
        except Exception as e:
            exception_dict = {
                'message': e.message,
                'args': e.args,
                'traceback': traceback.format_exc()
            }
            tracer.exceptions.append(exception_dict)


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
