"""
Main patcher module
"""

from __future__ import absolute_import
from .modules import MODULES


def patch_all():
    """
    Instrumenting all modules
    :return: None
    """
    for patch_module in MODULES:
        patch_module.patch()
