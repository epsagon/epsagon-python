"""General constants"""

import os

__version_info__ = ('0', '1', '2')
__version__ = '.'.join(__version_info__)

TC_REGIONS = [
    'us-east-1',
    'ap-southeast-2',
    'ap-northeast-11',
]

DEFAULT_REGION = 'us-east-1'
REGION = os.environ.get('AWS_REGION', DEFAULT_REGION)
if REGION not in TC_REGIONS:
    REGION = DEFAULT_REGION

TRACE_COLLECTOR_URL = "{protocol}{region}.tc.epsagon.com"
COLD_START = True

# How long we try to send traces
SEND_TIMEOUT = 1
