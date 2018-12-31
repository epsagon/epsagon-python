"""General constants"""

import os

__version__ = '1.0.23'

DEFAULT_REGION = 'us-east-1'
REGION = os.getenv('AWS_REGION', DEFAULT_REGION)

TRACE_COLLECTOR_URL = '{protocol}{region}.tc.epsagon.com'
COLD_START = True

# Customer original handler.
EPSAGON_HANDLER = 'EPSAGON_HANDLER'

# How long we try to send traces.
SEND_TIMEOUT = 1

MAX_LABEL_SIZE = 100 * 1024
