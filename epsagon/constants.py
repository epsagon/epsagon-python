"""General constants"""

import os

DEFAULT_REGION = 'us-east-1'
REGION = os.environ.get('AWS_REGION', DEFAULT_REGION)
TRACE_COLLECTOR_URL = 'http://tc.{0}.epsagon.com/'.format(REGION)
