import pytest
import urllib3
import epsagon.wrappers.python_function
from epsagon.trace import trace_factory
import epsagon.runners.python_function
import epsagon.constants


TEST_DOMAIN = 'jsonplaceholder.typicode.com'
TEST_PATH = '/todos/1'

def setup_function(func):
    trace_factory.use_single_trace = True
    epsagon.constants.COLD_START = True

def test_no_data_capture_with_urlopen(trace_transport):
    def use_urlopen():
        headers = {
            'Content-Type': 'application/json'
        }

        http = urllib3.PoolManager()
        conn = http.connection_from_url(TEST_DOMAIN)
        urllib_response = conn.urlopen(
            method='GET',
            url=TEST_PATH,
            body='',
            headers=headers,
            preload_content=False,
            decode_content=False,
        )
        return urllib_response

    response = use_urlopen()
    data = response.read()

    @epsagon.wrappers.python_function.python_wrapper
    def wrapped_function():
        return use_urlopen()

    wrapped_response = wrapped_function()
    wrapped_data = wrapped_response.read()
    # We expect in this case that the data will be available in the buffer
    assert(len(wrapped_data) > 0)
    assert(len(wrapped_response.data) == 0)
    urllib3_event = trace_transport.last_trace.events[-1]
    # Payload should not be collected in the case of raw-stream usage.
    assert(urllib3_event.resource['metadata']['response_body'] is None)
    # Compare un-instrumented vs instrumented data
    assert (len(data) > 0)
    assert (len(response.data) == 0)
    assert(wrapped_data == data)
    assert(wrapped_response.data == response.data)

@pytest.mark.parametrize("preload_content", [True, False])
def test_data_capture_with_pool_manager(preload_content, trace_transport):
    def use_poolmanager():
        headers = {
            'Content-Type': 'application/json'
        }

        http = urllib3.PoolManager()
        return http.request(
            'GET', TEST_DOMAIN + TEST_PATH,
            headers=headers, body='',
            preload_content=preload_content
        )

    response = use_poolmanager()
    data = response.read()

    @epsagon.wrappers.python_function.python_wrapper
    def wrapped_function():
        return use_poolmanager()

    wrapped_response = wrapped_function()
    wrapped_data = wrapped_response.read()
    if not preload_content:
        # In this case data will not be available in the buffer
        assert (len(wrapped_data) > 0)
        # But, data will not be stored in the `data` object
        assert (len(wrapped_response.data) == 0)
        # Compare un-instrumented vs instrumented data
        assert (len(data) > 0)
        assert (len(response.data) == 0)
    else:
        # In this case data will not be available in the buffer
        assert (len(wrapped_data) == 0)
        # But, data will be stored in the `data` object
        assert (len(wrapped_response.data) > 0)
        # Compare un-instrumented vs instrumented data
        assert (len(data) == 0)
        assert (len(response.data) > 0)
    assert(wrapped_data == data)
    assert(wrapped_response.data == response.data)
