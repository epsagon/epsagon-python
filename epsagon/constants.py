"""General constants"""

import os

__version__ = '1.0.27'

DEFAULT_REGION = 'us-east-1'
REGION = os.environ.get('AWS_REGION', DEFAULT_REGION)

TRACE_COLLECTOR_URL = "{protocol}{region}.tc.epsagon.com"
COLD_START = True

# How long we try to send traces in seconds.
SEND_TIMEOUT = 0.5

MAX_LABEL_SIZE = 100 * 1024
