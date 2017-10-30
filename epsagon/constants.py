"""General constants"""

import os

REGION = os.environ['AWS_REGION']
TRACE_COLLECTOR_URL = 'http://tc.{0}.epsagon.com/'.format(REGION)
