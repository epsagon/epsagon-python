"""General constants"""

import os

__version__ = '1.0.47'

DEFAULT_REGION = 'us-east-1'
REGION = os.getenv('AWS_REGION', DEFAULT_REGION)

TRACE_COLLECTOR_URL = '{protocol}{region}.tc.epsagon.com'
COLD_START = True

# Customer original handler.
EPSAGON_HANDLER = 'EPSAGON_HANDLER'

TIMEOUT_GRACE_TIME_MS = 200
# How long we try to send traces in seconds.
SEND_TIMEOUT = TIMEOUT_GRACE_TIME_MS / 1000.0

MAX_LABEL_SIZE = 100 * 1024
