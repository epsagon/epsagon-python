"""
Cloud Object Storage patcher module.
"""

from __future__ import absolute_import
import wrapt
from epsagon.modules.general_wrapper import wrapper
from ..events.qcloud_cos import COSEventFactory


def _wrapper(wrapped, instance, args, kwargs):
    """
    Cloud Object Storage wrapper for Tencent instrumentation.
    :param wrapped: wrapt's wrapped
    :param instance: wrapt's instance
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    :return: None
    """
    return wrapper(COSEventFactory, wrapped, instance, args, kwargs)


def patch():
    """
    patch module.
    :return: None
    """
    wrapt.wrap_function_wrapper(
        'qcloud_cos',
        'CosS3Client.send_request',
        _wrapper
    )
