"""
requests patcher module.
"""

from __future__ import absolute_import
import wrapt
from epsagon.modules.general_wrapper import wrapper
from ..events.requests import RequestsEventFactory
from ..constants import EPSAGON_MARKER
from ..utils import print_debug


def _wrapper(wrapped, instance, args, kwargs):
    """
    General wrapper for requests instrumentation.
    :param wrapped: wrapt's wrapped
    :param instance: wrapt's instance
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    :return: None
    """
    # Marking connection pool so requests won't be captured in urllib3 as well
    try:
        for adapter in instance.adapters.values():
            connection_pool = adapter.poolmanager.connection_from_url(
                args[0].url
            )
            setattr(connection_pool, EPSAGON_MARKER, True)
    except Exception as exception:  # pylint: disable=broad-except
        print_debug('Could not add marker to requests adapter: {}'.format(
            exception
        ))
    return wrapper(RequestsEventFactory, wrapped, instance, args, kwargs)


def patch():
    """
    Patch module.
    :return: None
    """

    wrapt.wrap_function_wrapper(
        'requests',
        'Session.send',
        _wrapper
    )
