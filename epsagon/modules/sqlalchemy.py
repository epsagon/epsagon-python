"""
sqlalchemy patcher module
"""
from __future__ import absolute_import

import wrapt
from epsagon.modules.general_wrapper import wrapper
from ..events.sqlalchemy import SQLAlchemyEventFactory


def _commit_wrapper(wrapped, instance, args, kwargs):
    wrapper(
        SQLAlchemyEventFactory,
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
        'sqlalchemy.orm.session',
        'Session.commit',
        _commit_wrapper
    )

    wrapt.wrap_function_wrapper(
        'sqlalchemy.orm.session',
        'Session.query',
        _commit_wrapper
    )
