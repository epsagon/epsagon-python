"""
Main patcher module
"""

from __future__ import absolute_import
from importlib import import_module
import epsagon.modules


def _import_exists(module_name):
    """
    Validates if import module exists
    :param module_name: module name to import
    :return: Bool
    """
    try:
        import_module(module_name)
        return True
    except ImportError:
        return False


def patch_all():
    """
    Instrumenting all modules
    :return: None
    """
    for patch_module in epsagon.modules.MODULES:
        if _import_exists(patch_module):
            try:
                epsagon.modules.MODULES[patch_module].patch()
            except Exception:  # pylint: disable=broad-except
                pass
