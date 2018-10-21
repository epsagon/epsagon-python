"""General constants"""

import os

__version__ = '1.0.10'

DEFAULT_REGION = 'us-east-1'
REGION = os.environ.get('AWS_REGION', DEFAULT_REGION)

TRACE_COLLECTOR_URL = "{protocol}{region}.tc.epsagon.com"
COLD_START = True

# How long we try to send traces.
SEND_TIMEOUT = 1

MAX_MESSAGE_SIZE = 512
