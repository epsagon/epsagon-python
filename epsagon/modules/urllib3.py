"""
urllib3 patcher module.
"""

from __future__ import absolute_import
import wrapt
from epsagon.modules.general_wrapper import wrapper
from ..events.urllib3 import Urllib3EventFactory


def _wrapper(wrapped, instance, args, kwargs):
    """
    General wrapper for requests instrumentation.
    :param wrapped: wrapt's wrapped
    :param instance: wrapt's instance
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    :return: None
    """
    return wrapper(Urllib3EventFactory, wrapped, instance, args, kwargs)


def patch():
    """
    Patch module.
    :return: None
    """

    try:
        wrapt.wrap_function_wrapper(
            'urllib3',
            'HTTPConnectionPool.urlopen',
            _wrapper
        )
    except Exception:  # pylint: disable=broad-except
        # Can happen in different Python versions.
        pass
