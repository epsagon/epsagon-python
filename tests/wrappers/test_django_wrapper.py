"""
Test Django wrapper functionality
"""

import pytest
import mock
from epsagon.wrappers.django import DjangoRequestMiddleware


TEST_BODY = 'test_body'
TEST_METHOD = 'test_method'
TEST_PATH = '/test_path'


@pytest.fixture
def test_request():
    """ A test request """
    class TestRequest:
        def __init__(self, path, method, body):
            self.path = path
            self.method = method
            self.body = body

        def get_host(self):
            return "test"

    return TestRequest(
        TEST_PATH,
        TEST_METHOD,
        TEST_BODY
    )


@mock.patch('epsagon.triggers.http.HTTPTriggerFactory')
@mock.patch('epsagon.runners.django.DjangoRunner')
@mock.patch('time.time', return_value=1)
def test_before_request(_, runner_mock, trigger_mock, test_request):
    """
    Test before_request generates a runner and a trigger.
    """
    request_mw = DjangoRequestMiddleware(test_request)

    request_mw.before_request()
    trigger_mock.factory.assert_called_once()

    runner_mock.assert_called_with(1, test_request)


@mock.patch('epsagon.triggers.http.HTTPTriggerFactory')
@mock.patch('epsagon.runners.django.DjangoRunner.update_response')
@mock.patch('time.time', return_value=1)
def test_after_request(
    _, runner_mock, trigger_mock, test_request, trace_transport
):
    """
    Test the whole  flow - a trace is generated with  the
    right content.
    """
    request_mw = DjangoRequestMiddleware(test_request)

    request_mw.before_request()
    request_mw.after_request({"content": "bla"})

    runner_mock.assert_called_once()
    trigger_mock.factory.assert_called_once()

    assert trace_transport.last_trace.events[
        0].resource['metadata']['Request Data'] == TEST_BODY
    assert trace_transport.last_trace.events[
        0].resource['metadata']['Path'] == TEST_PATH


@mock.patch('epsagon.triggers.http.HTTPTriggerFactory')
@mock.patch('epsagon.runners.django.DjangoRunner')
@mock.patch('time.time', return_value=1)
def test_ignored_path(_, runner_mock, trigger_mock, test_request):
    """
    Make sure we don't capture ignored pathes
    """
    ignored_request = test_request
    # JS files should be ignored
    ignored_request.path = "*.js"
    request_mw = DjangoRequestMiddleware(ignored_request)

    request_mw.before_request()
    trigger_mock.factory.assert_not_called()
