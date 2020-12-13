import pytest
import asynctest
import asyncio
from httpx import AsyncClient
from fastapi import FastAPI, APIRouter
from epsagon.common import ErrorCode
from epsagon.runners.fastapi import FastapiRunner

RETURN_VALUE = 'testresponsedata'
ROUTER_RETURN_VALUE = 'router-endpoint-return-data'
TEST_ROUTER_PREFIX = '/test-router-path'
TEST_ROUTER_PATH = '/test-router'

# test fastapi app handlers
async def handle():
    return RETURN_VALUE

async def handle_a():
    await asyncio.sleep(0.2)
    return "a"

async def handle_b():
    return "b"

async def handle_router_endpoint():
    return ROUTER_RETURN_VALUE

async def handle_error():
    raise Exception('test')


@pytest.fixture(scope='function', autouse=True)
def fastapi_app():
    app = FastAPI()
    app.add_api_route("/", handle, methods=["GET"])
    app.add_api_route("/a", handle_a, methods=["GET"])
    app.add_api_route("/b", handle_b, methods=["GET"])
    app.add_api_route("/err", handle_error, methods=["GET"])
    router = APIRouter()
    router.add_api_route(TEST_ROUTER_PATH, handle_router_endpoint)
    app.include_router(router, prefix=TEST_ROUTER_PREFIX)
    return app


@pytest.mark.asyncio
@asynctest.patch('epsagon.trace.trace_factory.use_async_tracer')
async def test_fastapi_sanity(_, trace_transport, fastapi_app):
    """Sanity test."""
    async with AsyncClient(app=fastapi_app, base_url="http://test") as ac:
        response = await ac.get("/?x=testval")
    response_data = response.json()
    runner = trace_transport.last_trace.events[0]
    assert isinstance(runner, FastapiRunner)
    assert runner.resource['name'].startswith('127.0.0.1')
    assert runner.resource['metadata']['Path'] == '/'
    assert runner.resource['metadata']['Response Data'] == RETURN_VALUE
    assert runner.resource['metadata']['Query Params'] == { 'x': 'testval'}
    assert response_data == RETURN_VALUE


@pytest.mark.asyncio
@asynctest.patch('epsagon.trace.trace_factory.use_async_tracer')
async def test_fastapi_custom_router(_, trace_transport, fastapi_app):
    """Custom router sanity test."""
    full_route_path= f'{TEST_ROUTER_PREFIX}{TEST_ROUTER_PATH}'
    async with AsyncClient(app=fastapi_app, base_url="http://test") as ac:
        response = await ac.get(full_route_path)
    response_data = response.json()
    runner = trace_transport.last_trace.events[0]
    assert isinstance(runner, FastapiRunner)
    assert runner.resource['name'].startswith('127.0.0.1')
    assert runner.resource['metadata']['Path'] == full_route_path
    assert runner.resource['metadata']['Response Data'] == ROUTER_RETURN_VALUE
    assert response_data == ROUTER_RETURN_VALUE


@pytest.mark.asyncio
@asynctest.patch('epsagon.trace.trace_factory.use_async_tracer')
async def test_fastapi_exception(_, trace_transport, fastapi_app):
    """Test when the handler got an exception."""
    try:
        async with AsyncClient(app=fastapi_app, base_url="http://test") as ac:
            _ = await ac.get("/err")
    except:
        pass

    runner = trace_transport.last_trace.events[0]
    assert runner.error_code == ErrorCode.EXCEPTION
    assert runner.exception['type'] == 'Exception'
    assert runner.exception['message'] == 'test'


@pytest.mark.asyncio
async def _send_request(app, path, trace_transport):
    """ Send request and validates its response & trace """
    request_path = f'/{path}'
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get(request_path)
    response_data = response.json()
    runner = trace_transport.last_trace.events[0]
    assert isinstance(runner, FastapiRunner)
    assert runner.resource['name'].startswith('127.0.0.1')
    assert runner.resource['metadata']['Path'] == request_path
    assert runner.resource['metadata']['Response Data'] == path
    assert response_data == path


@pytest.mark.asyncio
@asynctest.patch('epsagon.trace.trace_factory.use_async_tracer')
async def test_fastapi_multiple_requests(_, trace_transport, fastapi_app):
    """ Multiple requests test """
    for _ in range(3):
        await asyncio.gather(
            _send_request(fastapi_app, "a", trace_transport),
            _send_request(fastapi_app, "b", trace_transport)
        )
