import asynctest
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from epsagon.common import ErrorCode
#from epsagon.wrappers.fastapi import TracingAPIRoute
from epsagon.runners.fastapi import FastapiRunner


# Setting demo fastapi handlers
RETURN_VALUE = {
    'a': 'test',
    'b': 'test2',
}
async def handle():
    return RETURN_VALUE

async def handle_error():
    raise Exception('test')


@pytest.fixture(scope='function', autouse=True)
def fastapi_app():
    app = FastAPI()
    app.add_api_route("/", handle, methods=["GET"])
    app.add_api_route("/err", handle_error, methods=["GET"])
    return app


@pytest.fixture(scope='function', autouse=True)
def fastapi_client(fastapi_app):
    return TestClient(fastapi_app)

@asynctest.patch('epsagon.trace.trace_factory.use_async_tracer')
#@pytest.mark.asyncio
async def test_fastapi_sanity(trace_transport, fastapi_client):
    """Sanity test."""
    response = await fastapi_client.get('/')
    response_data = await response.json()
    runner = trace_transport.last_trace.events[0]
    assert isinstance(runner, FastapiRunner)
    assert runner.resource['name'].startswith('127.0.0.1')
    assert runner.resource['metadata']['Path'] == '/'
    assert runner.resource['metadata']['Response Data'] == RETURN_VALUE
    assert response_data == RETURN_VALUE
    assert False


@asynctest.patch('epsagon.trace.trace_factory.use_async_tracer')
#@pytest.mark.asyncio
async def test_fastapi_exception(trace_transport, fastapi_client):
    """Test when the handler got an exception."""
    try:
        client.get('/err')
    except:
        pass

    runner = trace_transport.last_trace.events[0]
    assert runner.error_code == ErrorCode.EXCEPTION
    assert runner.exception['type'] == 'Exception'
    assert runner.exception['message'] == 'test'
