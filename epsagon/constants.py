"""General constants"""

import os
import time

__version__ = '0.0.0'

DEFAULT_REGION = 'us-east-1'
REGION = os.getenv('AWS_REGION', DEFAULT_REGION)

TRACE_COLLECTOR_URL = '{protocol}{region}.tc.epsagon.com'
COLD_START = True
COLD_START_TIME = time.time()

DEBUG_MODE = ((os.getenv('EPSAGON_DEBUG') or '').upper() == 'TRUE')

# Customer original handler.
EPSAGON_HANDLER = 'EPSAGON_HANDLER'

DEFAULT_SEND_TIMEOUT_MS = 1000

TIMEOUT_GRACE_TIME_MS = int(os.getenv(
    'EPSAGON_LAMBDA_TIMEOUT_THRESHOLD_MS',
    str(DEFAULT_SEND_TIMEOUT_MS)
))
# How long we try to send traces in seconds.
TIMEOUT_ENV = float(os.getenv('EPSAGON_SEND_TIMEOUT_SEC', '0'))
SEND_TIMEOUT = TIMEOUT_ENV if TIMEOUT_ENV else TIMEOUT_GRACE_TIME_MS / 1000.0

MAX_LABEL_SIZE = 10 * 1024

DEFAULT_SAMPLE_RATE = 1

# User-defined HTTP minimum status code to be treated as an error.
HTTP_ERR_CODE = int(os.getenv('EPSAGON_HTTP_ERR_CODE', '500'))

# List of ignored endpoints for web frameworks.
IGNORED_ENDPOINTS = []

EPSAGON_MARKER = '__EPSAGON'
EPSAGON_HEADER = 'epsagon-trace-id'
# In some web frameworks, there is an automated capitalization
# for request headers
EPSAGON_HEADER_TITLE = 'Epsagon-Trace-Id'

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
    'activation_id',
    'hostname',
    'virtual_host',
    'region',
    'aws_account',
    'fragment_seq',
    'labels',
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
EPSAGON_EVENT_ID_KEY = '_epsagon_event_id'
TRACE_URL_PREFIX = (
    'https://app.epsagon.com/trace/{id}?timestamp={start_time}'
)
LAMBDA_TRACE_URL_PREFIX = (
    'https://app.epsagon.com/functions/{aws_account}/{region}/{function_name}'
    '?requestId={request_id}&requestTime={request_time}'
)
