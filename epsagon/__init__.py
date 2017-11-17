from __future__ import absolute_import
from . import wrapper
from .patcher import patch_all

patch_all()
init = wrapper.init
lambda_wrapper = wrapper.lambda_wrapper
azure_wrapper = wrapper.azure_wrapper
