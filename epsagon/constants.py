"""General constants"""

import os

__version__ = '0.0.0'

DEFAULT_REGION = 'us-east-1'
REGION = os.getenv('AWS_REGION', DEFAULT_REGION)

TRACE_COLLECTOR_URL = '{protocol}{region}.tc.epsagon.com'
COLD_START = True

# Customer original handler.
EPSAGON_HANDLER = 'EPSAGON_HANDLER'

TIMEOUT_GRACE_TIME_MS = 200
# How long we try to send traces in seconds.
TIMEOUT_ENV = float(os.getenv('EPSAGON_SEND_TIMEOUT_SEC', '0'))
SEND_TIMEOUT = TIMEOUT_ENV if TIMEOUT_ENV else TIMEOUT_GRACE_TIME_MS / 1000.0

MAX_LABEL_SIZE = 100 * 1024

# User-defined HTTP minimum status code to be treated as an error.
HTTP_ERR_CODE = int(os.getenv('EPSAGON_HTTP_ERR_CODE', '500'))

# List of ignored endpoints for web frameworks.
IGNORED_ENDPOINTS = []

STRONG_KEYS = [
    'key',
    'request_id',
    'requestid',
    'request-id',
    'steps_dict',
    'message_id',
    'etag',
    'item_hash',
    'sequence_number',
    'trace_id',
    'job_id',
    'activation_id'
]


def is_strong_key(key):
    """
    Checks if given key is a strong key
    :param key: key
    :return: is a strong key
    """
    key = key.replace(' ', '_').lower()
    for strong_key in STRONG_KEYS:
        if strong_key in key:
            return True
    return False


STEP_DICT_NAME = 'Epsagon'
