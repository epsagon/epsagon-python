"""
Epsagon's init.
"""

from __future__ import absolute_import
import os
from .wrappers import lambda_wrapper, azure_wrapper, python_wrapper
from .trace import init
from .patcher import patch_all

__all__ = ['lambda_wrapper', 'azure_wrapper', 'python_wrapper', 'init']

# The modules are patched only if DISABLE_EPSAGON_PATCH variable is NOT 'TRUE'
if os.environ.get('DISABLE_EPSAGON_PATCH') != 'TRUE':
    patch_all()
