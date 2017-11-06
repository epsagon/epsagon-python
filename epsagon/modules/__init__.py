from __future__ import absolute_import
from . import botocore
from . import requests
from . import grpc

MODULES = {
    'botocore': botocore,
    'requests': requests,
    'grpc': grpc,
}