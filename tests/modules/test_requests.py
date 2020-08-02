import epsagon.wrappers.python_function
from epsagon.trace import trace_factory
import epsagon.runners.python_function
import epsagon.constants
import mock
import requests

TEST_URL = 'https://test.com/'

def setup_function(func):
    trace_factory.use_single_trace = True
    epsagon.constants.COLD_START = True

@mock.patch('urllib3.poolmanager.PoolManager.connection_from_url')
def test_pool_manager_patching(pool_manager_mock):
    retval = 'success'

    @epsagon.wrappers.python_function.python_wrapper
    def wrapped_function():
        requests.get(TEST_URL)
        return retval

    assert wrapped_function() == retval
    pool_manager_mock.assert_called_with(TEST_URL)
