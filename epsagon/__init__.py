from __future__ import absolute_import
from . import wrapper
from .patcher import patch_all

__version_info__ = ('0', '1', '0')
__version__ = '.'.join(__version_info__)

patch_all()
lambda_wrapper = wrapper.lambda_wrapper
azure_wrapper = wrapper.azure_wrapper
