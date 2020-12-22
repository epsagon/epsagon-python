import threading
import pytest
import mock
from flask import Flask, request
from epsagon import trace_factory
from epsagon.wrappers.flask import FlaskWrapper
from time import sleep
from .common import multiple_threads_handler

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


@app_test.route('/multiple_threads')
def multiple_threads_route():
    multiple_threads_handler()
    return "multiple_threads"


@pytest.fixture
def client():
    """ A test client that has the Authorization header """
    app_test.testing = True
    app = app_test.test_client()
    return app


CLIENT = app_test.test_client()


@app_test.route('/self_call', methods=["POST"])
def self_call():
    json_data = request.get_json()
    inner_call = None
    if json_data:
        inner_call = json_data['inner_call']

    if not inner_call:
        return CLIENT.post('/self_call', json={
            'inner_call': 'True'
        })

    return RETURN_VALUE

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
@mock.patch('epsagon.trace.trace_factory.get_trace')
def test_flask_wrapper_teardown_request(get_trace_mock, create_trace_mock, _, client):
    """Test tracer gets new event and send it on new request."""
    client.get('/')
    create_trace_mock().set_runner.assert_called_once()
    get_trace_mock().send_traces.assert_called_once()


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


def test_call_to_self(trace_transport, client):
    """
    And API that calls itself. Make sure instrumentation doesn't throw
    and exception that gets to the user.
    """
    result = CLIENT.post('/self_call')
    assert result.data.decode('ascii') == RETURN_VALUE


def test_flask_wrapper_route_multiple_threads(trace_transport, client):
    """
    Makes a request to a route which invokes multiple threads
    perfoming http requests.
    Make sure no trace is created for those threads.
    """
    role = 'multiple_threads'
    result = client.get('/{}'.format(role))
    validate_response(role, result, trace_transport)
    # validating no `zombie` traces exist
    assert not trace_factory.traces
