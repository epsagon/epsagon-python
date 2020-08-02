import threading
import pytest
import mock
from flask import Flask, request
from epsagon import trace_factory
from epsagon.wrappers.flask import FlaskWrapper
from time import sleep

# Setting demo Flask app
RETURN_VALUE = 'a'
app_test = Flask('test')
FlaskWrapper(app_test)


def setup_function(func):
    trace_factory.use_single_trace = False


@app_test.route('/')
def test():
    return RETURN_VALUE


@app_test.route('/a')
def a_route():
    sleep(0.1)
    return "a"


@app_test.route('/b')
def b_route():
    return "b"


@app_test.route('/error')
def error():
    raise Exception('test')


@pytest.fixture
def client():
    """ A test client that has the Authorization header """
    app_test.testing = True
    app = app_test.test_client()
    return app


###


@mock.patch('warnings.warn')
@mock.patch('epsagon.triggers.http.HTTPTriggerFactory')
@mock.patch('epsagon.runners.flask.FlaskRunner')
@mock.patch('time.time', return_value=1)
def test_flask_wrapper_before_request(_, runner_mock, trigger_mock, __, client):
    """Test runner and trigger init on new request."""
    result = client.get('/')

    runner_mock.assert_called_with(1, app_test, request)
    trigger_mock.factory.assert_called_once()

    assert result.data.decode('ascii') == RETURN_VALUE


@mock.patch('warnings.warn')
@mock.patch('epsagon.runners.flask.FlaskRunner.update_response')
def test_flask_wrapper_after_request(runner_mock, _, client):
    """Test update response called on new request."""
    client.get('/')

    runner_mock.assert_called_once()


@mock.patch('warnings.warn')
@mock.patch('epsagon.trace.trace_factory.get_or_create_trace')
def test_flask_wrapper_teardown_request(trace_mock, _, client):
    """Test tracer gets new event and send it on new request."""
    client.get('/')
    trace_mock().set_runner.assert_called_once()
    trace_mock().send_traces.assert_called_once()


@mock.patch('warnings.warn')
@mock.patch('epsagon.runners.flask.FlaskRunner.set_exception')
def test_flask_wrapper_teardown_exception(exception_mock, _, client):
    """Test runner gets an exception on error request."""
    with pytest.raises(Exception):
        client.get('/error')

        exception_mock.assert_called_once()


@mock.patch(
    'epsagon.trace.trace_factory.get_or_create_trace',
    side_effect=lambda: trace_mock
)
def test_lambda_wrapper_multi_thread(_):
    assert not trace_factory.use_single_trace


def validate_response(role, result, trace_transport):
    """
    Validate Epsagon trace was generated the right way,
    and that the response matches what we expect
    """
    assert trace_transport.last_trace.events[0].resource[
        'metadata']['Response Data'].decode('ascii') == role
    assert result.data.decode('ascii') == role


def thread_client(role, trace_transport, client):
    """
    Get a string from an endpoint, and validate Epsagon
    trace and response
    """
    result = client.get('/{0}'.format(role))
    validate_response(role, result, trace_transport)


def test_flask_wrapper_multiple_requests(trace_transport, client):
    """
    Make 2 simulatanous requests.
    Make sure none of the responses or generated traces mix up.
    """
    a = threading.Thread(target=thread_client, args=(
        'a', trace_transport, client))
    b = threading.Thread(target=thread_client, args=(
        'b', trace_transport, client))

    for thread in [a, b]:
        thread.start()

    for thread in [a, b]:
        thread.join()
