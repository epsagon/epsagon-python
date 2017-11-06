"""
Main patcher module
"""

from __future__ import absolute_import
from .modules import MODULES


def _import_exists(module_name):
    """
    Validates if import module exists
    :param module_name: module name to import
    :return: Bool
    """
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False


def patch_all():
    """
    Instrumenting all modules
    :return: None
    """
    for patch_module in MODULES:
        if _import_exists(patch_module):
            MODULES[patch_module].patch()
