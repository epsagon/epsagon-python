"""
sqlalchemy patcher module
"""
from __future__ import absolute_import

from epsagon.modules.general_wrapper import wrapper
from ..events.sqlalchemy import SqlAlchemyEventFactory
from ..utils import patch_once


def _wrapper(wrapped, instance, args, kwargs):
    """
    General wrapper for sqlalchemy instrumentation.
    :param wrapped: wrapt's wrapped
    :param instance: wrapt's instance
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    :return: None
    """
    return wrapper(SqlAlchemyEventFactory, wrapped, instance, args, kwargs)

def patch():
    """
    patch module.
    :return: None
    """

    patch_once(
        'sqlalchemy.orm.session',
        'Session.__init__',
        _wrapper
    )

    patch_once(
        'sqlalchemy.orm.session',
        'Session.close',
        _wrapper
    )
