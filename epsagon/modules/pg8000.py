# pylint: disable=C0103
"""
PG8000 patcher module
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
        'pg8000',
        'connect',
        connect_wrapper
    )
