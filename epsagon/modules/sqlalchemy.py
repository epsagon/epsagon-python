"""
sqlalchemy patcher module.
"""

from __future__ import absolute_import
import wrapt
from epsagon.modules.general_wrapper import wrapper
from ..events.sqlalchemy import SQLAlchemyEventFactory


def _commit_wrapper(wrapped, instance, args, kwargs):
    """
    Commit wrapper for sqlalchemy instrumentation.
    :param wrapped: wrapt's wrapped
    :param instance: wrapt's instance
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    :return: None
    """

    return wrapper(SQLAlchemyEventFactory, wrapped, instance, args, kwargs)


def patch():
    """
    Patch module.
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
