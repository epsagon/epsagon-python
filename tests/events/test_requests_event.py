"""
Requests tests
"""
import requests
from epsagon.trace import trace_factory
from epsagon.events.requests import RequestsEvent

RESPONSE_DATA = b'test data'
TEST_PATH = '/'

def setup_function():
    trace_factory.metadata_only = False
    trace_factory.use_single_trace = True
    trace_factory.get_or_create_trace()


def teardown_function():
    trace_factory.singleton_trace = None


def _get_active_trace():
    return trace_factory.active_trace

def _validate_request_event_metadata(event):
    assert event.resource["operation"] == 'GET'
    assert event.RESOURCE_TYPE == 'http'


def test_get_request_sanity(httpserver):
    """
    Tests get request sanity
    """
    httpserver.expect_request(TEST_PATH).respond_with_data(RESPONSE_DATA)
    response = requests.get(httpserver.url_for(TEST_PATH))
    trace = _get_active_trace()
    event = trace.events[0]
    _validate_request_event_metadata(event)
    assert(response.content) == RESPONSE_DATA

def test_get_request_stream(httpserver):
    """
    Tests get request sanity
    """
    httpserver.expect_request(TEST_PATH).respond_with_data(RESPONSE_DATA)
    response = requests.get(httpserver.url_for(TEST_PATH), stream=True)
    trace = _get_active_trace()
    event = trace.events[0]
    _validate_request_event_metadata(event)
    assert(response.raw.read()) == RESPONSE_DATA
