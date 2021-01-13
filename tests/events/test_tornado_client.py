import epsagon.wrappers.python_function
import epsagon.runners.python_function
import epsagon.constants
import mock
from tornado.httpclient import AsyncHTTPClient

TEST_URL = 'https://example.test/'


@mock.patch('epsagon.trace.TraceFactory.add_event')
def test_sanity(add_event_mock):
    retval = 'success'

    @epsagon.wrappers.python_function.python_wrapper
    def wrapped_function():
        http_client = AsyncHTTPClient()
        http_client.fetch(TEST_URL)
        return retval
    assert wrapped_function() == retval
    add_event_mock.assert_called()
    event = add_event_mock.call_args_list[0].args[0]
    assert event.resource['name'] == 'example.test'
    assert event.resource['operation'] == 'GET'
    assert event.resource['type'] == 'http'
    assert 'http_trace_id' in event.resource['metadata']
