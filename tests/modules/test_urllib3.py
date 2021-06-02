import urllib3
import epsagon.wrappers.python_function
from epsagon.trace import trace_factory
import epsagon.runners.python_function
import epsagon.constants


TEST_URL = 'https://google.com/'

def setup_function(func):
    trace_factory.use_single_trace = True
    epsagon.constants.COLD_START = True

def test_no_data_capture_on_preload_content_false(trace_transport):
    @epsagon.wrappers.python_function.python_wrapper
    def wrapped_function():
        headers = {
            'Content-Type': 'application/json'
        }

        http = urllib3.PoolManager()
        conn = http.connection_from_url(TEST_URL)
        urllib_response = conn.urlopen(
            method='POST',
            url='/index.html',
            body='',
            headers=headers,
            preload_content=False,
            decode_content=False,
        )
        return urllib_response

    response = wrapped_function()
    data = response.read()
    # We expect in this case that the data will be available in the buffer
    assert(len(data) > 0)
    urllib3_event = trace_transport.last_trace.events[-1]
    # Payload should not be collected in the case of raw-stream usage.
    assert(urllib3_event.resource['metadata']['response_body'] is None)

def test_data_capture_on_preload_content_true(trace_transport):
    @epsagon.wrappers.python_function.python_wrapper
    def wrapped_function():
        headers = {
            'Content-Type': 'application/json'
        }

        http = urllib3.PoolManager()
        return http.request('POST', TEST_URL, headers=headers, body='', preload_content=True)

    response = wrapped_function()
    data = response.read()
    # In this case data will not be available in the buffer
    assert (len(data) == 0)
    # But, data will be stored in the `data` object
    assert (len(response.data) > 0)
    urllib3_event = trace_transport.last_trace.events[-1]
    # Payload will be collected and stored inside the event data
    assert(len(urllib3_event.resource['metadata']['response_body']) > 0)
