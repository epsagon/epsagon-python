"""
FastAPI wrapper tests
"""
import time
import pytest
import asynctest
import asyncio
from httpx import AsyncClient
from fastapi import FastAPI, APIRouter
from fastapi.responses import JSONResponse
from epsagon import trace_factory
from epsagon.common import ErrorCode
from epsagon.runners.fastapi import FastapiRunner
from .common import multiple_threads_handler

RETURN_VALUE = 'testresponsedata'
ROUTER_RETURN_VALUE = 'router-endpoint-return-data'
TEST_ROUTER_PREFIX = '/test-router-path'
TEST_ROUTER_PATH = '/test-router'
MULTIPLE_THREADS_KEY = "multiple_threads"
MULTIPLE_THREADS_ROUTE = f'/{MULTIPLE_THREADS_KEY}'
MULTIPLE_THREADS_RETURN_VALUE = MULTIPLE_THREADS_KEY

def _get_response_data(key):
    return {key: key}

def _get_response(key):
    return JSONResponse(content=_get_response_data(key))

# test fastapi app handlers
async def handle():
    return _get_response(RETURN_VALUE)

def handle_sync():
    return _get_response(RETURN_VALUE)

async def handle_a():
    await asyncio.sleep(0.2)
    return _get_response('a')

def handle_a_sync():
    time.sleep(0.2)
    return _get_response('a')

async def handle_b():
    return _get_response('b')

def handle_b_sync():
    return _get_response('b')

async def handle_router_endpoint():
    return _get_response(ROUTER_RETURN_VALUE)

def handle_router_endpoint_sync():
    return _get_response(ROUTER_RETURN_VALUE)

async def multiple_threads_route():
    multiple_threads_handler()
    return _get_response(MULTIPLE_THREADS_RETURN_VALUE)

def multiple_threads_route_sync():
    multiple_threads_handler()
    return _get_response(MULTIPLE_THREADS_RETURN_VALUE)


class CustomFastAPIException(Exception):
    pass

async def handle_error():
    raise CustomFastAPIException('test')

def handle_error_sync():
    raise CustomFastAPIException('test')


@pytest.fixture(scope='function', autouse=False)
def async_fastapi_app():
    app = FastAPI()
    app.add_api_route("/", handle, methods=["GET"])
    app.add_api_route("/a", handle_a, methods=["GET"])
    app.add_api_route("/b", handle_b, methods=["GET"])
    app.add_api_route("/err", handle_error, methods=["GET"])
    app.add_api_route(MULTIPLE_THREADS_ROUTE, multiple_threads_route, methods=["GET"])
    router = APIRouter()
    router.add_api_route(TEST_ROUTER_PATH, handle_router_endpoint)
    app.include_router(router, prefix=TEST_ROUTER_PREFIX)
    return app

@pytest.fixture(scope='function', autouse=False)
def sync_fastapi_app():
    app = FastAPI()
    app.add_api_route("/", handle_sync, methods=["GET"])
    app.add_api_route("/a", handle_a_sync, methods=["GET"])
    app.add_api_route("/b", handle_b_sync, methods=["GET"])
    app.add_api_route("/err", handle_error_sync, methods=["GET"])
    app.add_api_route(MULTIPLE_THREADS_ROUTE, multiple_threads_route_sync, methods=["GET"])
    router = APIRouter()
    router.add_api_route(TEST_ROUTER_PATH, handle_router_endpoint_sync)
    app.include_router(router, prefix=TEST_ROUTER_PREFIX)
    return app

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fastapi_app",
    [
        pytest.lazy_fixture("sync_fastapi_app"),
        pytest.lazy_fixture("async_fastapi_app"),
    ],
)
async def test_fastapi_sanity(trace_transport, fastapi_app):
    """Sanity test."""
    async with AsyncClient(app=fastapi_app, base_url="http://test") as ac:
        response = await ac.get("/?x=testval")
    response_data = response.json()
    runner = trace_transport.last_trace.events[0]
    assert isinstance(runner, FastapiRunner)
    assert runner.resource['name'].startswith('127.0.0.1')
    assert runner.resource['metadata']['Path'] == '/'
    expected_response_data = _get_response_data(RETURN_VALUE)
    assert runner.resource['metadata']['Response Data'] == (
        expected_response_data
    )
    assert runner.resource['metadata']['Query Params'] == { 'x': 'testval'}
    assert response_data == expected_response_data


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fastapi_app",
    [
        pytest.lazy_fixture("sync_fastapi_app"),
        pytest.lazy_fixture("async_fastapi_app"),
    ],
)
async def test_fastapi_custom_router(trace_transport, fastapi_app):
    """Custom router sanity test."""
    full_route_path= f'{TEST_ROUTER_PREFIX}{TEST_ROUTER_PATH}'
    async with AsyncClient(app=fastapi_app, base_url="http://test") as ac:
        response = await ac.get(full_route_path)
    response_data = response.json()
    runner = trace_transport.last_trace.events[0]
    assert isinstance(runner, FastapiRunner)
    assert runner.resource['name'].startswith('127.0.0.1')
    assert runner.resource['metadata']['Path'] == full_route_path
    expected_response_data = _get_response_data(ROUTER_RETURN_VALUE)
    assert runner.resource['metadata']['Response Data'] == (
        expected_response_data
    )
    assert response_data == expected_response_data


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fastapi_app",
    [
        pytest.lazy_fixture("sync_fastapi_app"),
        pytest.lazy_fixture("async_fastapi_app"),
    ],
)
async def test_fastapi_exception(trace_transport, fastapi_app):
    """Test when the handler got an exception."""
    try:
        async with AsyncClient(app=fastapi_app, base_url="http://test") as ac:
            _ = await ac.get("/err")
    except CustomFastAPIException:
        pass

    runner = trace_transport.last_trace.events[0]
    assert runner.error_code == ErrorCode.EXCEPTION
    assert runner.exception['type'] == 'CustomFastAPIException'
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
    expected_response_data = _get_response_data(path)
    assert runner.resource['metadata']['Response Data'] == (
        expected_response_data
    )
    assert response_data == expected_response_data


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fastapi_app",
    [
        pytest.lazy_fixture("sync_fastapi_app"),
        pytest.lazy_fixture("async_fastapi_app"),
    ],
)
async def test_fastapi_multiple_requests(trace_transport, fastapi_app):
    # used to reset trace factory between fastapi apps
    trace_factory.use_single_trace = True
    """ Multiple requests test """
    for _ in range(3):
        await asyncio.gather(
            _send_request(fastapi_app, "a", trace_transport),
            _send_request(fastapi_app, "b", trace_transport)
        )



@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fastapi_app",
    [
        pytest.lazy_fixture("sync_fastapi_app"),
        pytest.lazy_fixture("async_fastapi_app"),
    ],
)
async def test_fastapi_multiple_threads_route(trace_transport, fastapi_app):
    """
    Tests request to a route, which invokes multiple threads.
    Validating no `zombie` traces exist (fromn the callback invoked threads)
    """
    async with AsyncClient(app=fastapi_app, base_url="http://test") as ac:
        response = await ac.get(f"{MULTIPLE_THREADS_ROUTE}?x=testval")
    response_data = response.json()
    # expects only 1 event. The new threads events shouldn't belong this trace
    assert len(trace_transport.last_trace.events) == 1
    runner = trace_transport.last_trace.events[0]
    assert isinstance(runner, FastapiRunner)
    assert runner.resource['name'].startswith('127.0.0.1')
    assert runner.resource['metadata']['Path'] == MULTIPLE_THREADS_ROUTE
    expected_response_data = _get_response_data(MULTIPLE_THREADS_RETURN_VALUE)
    assert runner.resource['metadata']['Response Data'] == (
        expected_response_data
    )
    assert runner.resource['metadata']['Query Params'] == { 'x': 'testval'}
    assert response_data == expected_response_data
    # validating no `zombie` traces exist
    assert not trace_factory.traces
