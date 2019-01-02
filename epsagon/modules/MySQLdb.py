# pylint: disable=C0103
"""
MySQLdb patcher module
"""
from __future__ import absolute_import

import wrapt
from .db_wrapper import connect_wrapper


def patch():
    """
    patch module.
    :return: None
    """
    wrapt.wrap_function_wrapper(
        'MySQLdb',
        'connect',
        connect_wrapper
    )
    wrapt.wrap_function_wrapper(
        'MySQLdb',
        'Connection',
        connect_wrapper
    )
    wrapt.wrap_function_wrapper(
        'MySQLdb',
        'Connect',
        connect_wrapper
    )
