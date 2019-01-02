"""
pymysql patcher module
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
        'pymysql',
        'connect',
        connect_wrapper
    )
