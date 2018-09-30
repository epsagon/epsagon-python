import pytest
import mock
from flask import Flask, request
import epsagon
from epsagon.wrappers.flask import FlaskWrapper


# Setting demo Flask app
epsagon.init(token='test', app_name='FlaskApp')
RETURN_VALUE = 'a'
app_test = Flask('test')
FlaskWrapper(app_test)


@app_test.route('/')
def test():
    return RETURN_VALUE


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
@mock.patch('epsagon.trace.tracer')
def test_flask_wrapper_teardown_request(trace_mock, _, client):
    """Test tracer gets new event and send it on new request."""
    client.get('/')

    trace_mock.add_event.assert_called_once()
    trace_mock.send_traces.assert_called_once()


@mock.patch('warnings.warn')
@mock.patch('epsagon.runners.flask.FlaskRunner.set_exception')
def test_flask_wrapper_teardown_exception(exception_mock, _, client):
    """Test runner gets an exception on error request."""
    with pytest.raises(Exception):
        client.get('/error')

        exception_mock.assert_called_once()
