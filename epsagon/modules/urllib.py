"""
requests patcher module.
"""

from __future__ import absolute_import
from epsagon.utils import patch_once
from epsagon.modules.general_wrapper import wrapper
from ..events.urllib import UrllibEventFactory


def _wrapper(wrapped, instance, args, kwargs):
    """
    General wrapper for requests instrumentation.
    :param wrapped: wrapt's wrapped
    :param instance: wrapt's instance
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    :return: None
    """
    return wrapper(UrllibEventFactory, wrapped, instance, args, kwargs)


def patch():
    """
    Patch module.
    :return: None
    """

    try:
        patch_once(
            'urllib.request',
            'OpenerDirector._open',
            _wrapper
        )
    except Exception:  # pylint: disable=broad-except
        # Can happen in different Python versions.
        pass
