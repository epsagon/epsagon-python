"""General constants"""

import os

__version_info__ = ('0', '1', '0')
__version__ = '.'.join(__version_info__)

DEFAULT_REGION = 'eu-central-1'
REGION = os.environ.get('AWS_REGION', DEFAULT_REGION)
TRACE_COLLECTOR_URL = 'http://tc.{0}.epsagon.com/'.format(REGION)
COLD_START = True
