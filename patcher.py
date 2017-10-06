"""
Main patcher module
"""

import patch_botocore
import patch_requests

PATCHED_MODULES = [
    patch_requests,
    patch_botocore
]


def patch_all():
    """
    Instrumenting all modules
    :return: None
    """
    for patch_module in PATCHED_MODULES:
        patch_module.patch()
