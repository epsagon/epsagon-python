"""
FastAPI wrapper tests
"""
import time
import pytest
import asynctest
import asyncio
from typing import List
from httpx import AsyncClient
from pydantic import BaseModel
from fastapi import FastAPI, APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from epsagon import trace_factory
from epsagon.common import ErrorCode
from epsagon.runners.fastapi import FastapiRunner
from .common import multiple_threads_handler

RETURN_VALUE = 'testresponsedata'
ROUTER_RETURN_VALUE = 'router-endpoint-return-data'
REQUEST_OBJ_PATH = '/given_request'
TEST_ROUTER_PREFIX = '/test-router-path'
TEST_ROUTER_PATH = '/test-router'
MULTIPLE_THREADS_KEY = "multiple_threads"
MULTIPLE_THREADS_ROUTE = f'/{MULTIPLE_THREADS_KEY}'
MULTIPLE_THREADS_RETURN_VALUE = MULTIPLE_THREADS_KEY
TEST_POST_DATA = {'post_test': '123'}
CUSTOM_RESPONSE = ["A"]
CUSTOM_RESPONSE_PATH = "/custom_response"
BASE_MODEL_RESPONSE_PATH = "/base_model_response"
DEFAULT_STATUS_CODE = 200
CUSTOM_STATUS_CODE = 202
CUSTOM_STATUS_CODE_PATH = "/custom_status_code"
OVERRIDDEN_CUSTOM_STATUS_CODE_PATH = "/overridden_custom_status_code"

class CustomBaseModel(BaseModel):
    data: List[str]

def _get_response_data(key):
    return {key: key}

def _get_response(key):
    return JSONResponse(content=_get_response_data(key))

# test fastapi app handlers
def handle():
    return _get_response(RETURN_VALUE)

def handle_custom_response(response_model=List[str]):
    return CUSTOM_RESPONSE

def handle_base_model_response(response_model=CustomBaseModel):
    return CustomBaseModel(data=CUSTOM_RESPONSE)

def handle_custom_status_code(response_model=List[str]):
    return CUSTOM_RESPONSE

def handle_overridden_custom_status_code():
    return _get_response(RETURN_VALUE)

def handle_given_request(request: Request):
    assert request.method == 'POST'
    loop = None
    try:
        loop = asyncio.new_event_loop()
        assert loop.run_until_complete(request.json()) == TEST_POST_DATA
    finally:
        if loop:
            loop.close()
    return _get_response(RETURN_VALUE)

def handle_a():
    time.sleep(0.2)
    return _get_response('a')

def handle_b():
    return _get_response('b')

def handle_router_endpoint():
    return _get_response(ROUTER_RETURN_VALUE)

def multiple_threads_route():
    multiple_threads_handler()
    return _get_response(MULTIPLE_THREADS_RETURN_VALUE)


class CustomFastAPIException(Exception):
    pass

def handle_error():
    raise CustomFastAPIException('test')


@pytest.fixture(scope='function', autouse=False)
def fastapi_app():
    app = FastAPI()
    app.add_api_route("/", handle, methods=["GET"])
    app.add_api_route(
        CUSTOM_RESPONSE_PATH,
        handle_custom_response,
        methods=["GET"]
    )
    app.add_api_route(
        BASE_MODEL_RESPONSE_PATH,
        handle_base_model_response,
        methods=["GET"]
    )
    app.add_api_route(
        CUSTOM_STATUS_CODE_PATH,
        handle_custom_status_code,
        methods=["GET"],
        status_code=CUSTOM_STATUS_CODE
    )
    app.add_api_route(
        OVERRIDDEN_CUSTOM_STATUS_CODE_PATH,
        handle_overridden_custom_status_code,
        methods=["GET"],
        status_code=CUSTOM_STATUS_CODE
    )
    app.add_api_route(REQUEST_OBJ_PATH, handle_given_request, methods=["POST"])
    app.add_api_route("/a", handle_a, methods=["GET"])
    app.add_api_route("/b", handle_b, methods=["GET"])
    app.add_api_route("/err", handle_error, methods=["GET"], status_code=200)
    app.add_api_route(MULTIPLE_THREADS_ROUTE, multiple_threads_route, methods=["GET"])
    router = APIRouter()
    router.add_api_route(TEST_ROUTER_PATH, handle_router_endpoint)
    app.include_router(router, prefix=TEST_ROUTER_PREFIX)
    return app


@pytest.mark.asyncio
async def test_fastapi_sanity(trace_transport, fastapi_app):
    """Sanity test."""
    async with AsyncClient(app=fastapi_app, base_url="http://test") as ac:
        response = await ac.get("/?x=testval")
    response_data = response.json()
    runner = trace_transport.last_trace.events[0]
    assert isinstance(runner, FastapiRunner)
    assert runner.resource['name'].startswith('127.0.0.1')
    assert runner.resource['metadata']['Path'] == '/'
    assert runner.resource['metadata']['status_code'] == DEFAULT_STATUS_CODE
    expected_response_data = _get_response_data(RETURN_VALUE)
    assert runner.resource['metadata']['Response Data'] == (
        expected_response_data
    )
    assert runner.resource['metadata']['Query Params'] == { 'x': 'testval'}
    assert response_data == expected_response_data
    # validating no `zombie` traces exist
    assert not trace_factory.traces


@pytest.mark.asyncio
async def test_fastapi_custom_response(trace_transport, fastapi_app):
    """custom response test."""
    request_path = f'{CUSTOM_RESPONSE_PATH}?x=testval'
    async with AsyncClient(app=fastapi_app, base_url="http://test") as ac:
        response = await ac.get(request_path)
    response_data = response.json()
    runner = trace_transport.last_trace.events[0]
    assert isinstance(runner, FastapiRunner)
    assert runner.resource['name'].startswith('127.0.0.1')
    assert runner.resource['metadata']['Path'] == CUSTOM_RESPONSE_PATH
    assert runner.resource['metadata']['status_code'] == DEFAULT_STATUS_CODE
    assert runner.resource['metadata']['Query Params'] == { 'x': 'testval'}
    assert runner.resource['metadata']['Response Data'] == (
        jsonable_encoder(CUSTOM_RESPONSE)
    )
    assert response_data == CUSTOM_RESPONSE
    # validating no `zombie` traces exist
    assert not trace_factory.traces


@pytest.mark.asyncio
async def test_fastapi_base_model_response(trace_transport, fastapi_app):
    """base model response test."""
    request_path = f'{BASE_MODEL_RESPONSE_PATH}?x=testval'
    async with AsyncClient(app=fastapi_app, base_url="http://test") as ac:
        response = await ac.get(request_path)
    response_data = response.json()
    runner = trace_transport.last_trace.events[0]
    expected_response_data = CustomBaseModel(data=CUSTOM_RESPONSE)
    assert isinstance(runner, FastapiRunner)
    assert runner.resource['name'].startswith('127.0.0.1')
    assert runner.resource['metadata']['Path'] == BASE_MODEL_RESPONSE_PATH
    assert runner.resource['metadata']['status_code'] == DEFAULT_STATUS_CODE
    assert runner.resource['metadata']['Query Params'] == { 'x': 'testval'}
    assert runner.resource['metadata']['Response Data'] == (
        jsonable_encoder(expected_response_data)
    )
    assert response_data == expected_response_data
    # validating no `zombie` traces exist
    assert not trace_factory.traces


@pytest.mark.asyncio
async def test_fastapi_custom_status_code(trace_transport, fastapi_app):
    """custom status code test."""
    request_path = f'{CUSTOM_STATUS_CODE_PATH}?x=testval'
    async with AsyncClient(app=fastapi_app, base_url="http://test") as ac:
        response = await ac.get(request_path)
    response_data = response.json()
    runner = trace_transport.last_trace.events[0]
    assert isinstance(runner, FastapiRunner)
    assert runner.resource['name'].startswith('127.0.0.1')
    assert runner.resource['metadata']['Path'] == CUSTOM_STATUS_CODE_PATH
    assert runner.resource['metadata']['status_code'] == CUSTOM_STATUS_CODE
    assert runner.resource['metadata']['Query Params'] == { 'x': 'testval'}
    assert runner.resource['metadata']['Response Data'] == (
        jsonable_encoder(CUSTOM_RESPONSE)
    )
    assert runner.resource['metadata']['Query Params'] == { 'x': 'testval'}
    assert runner.resource['metadata']['Response Data'] == (
        jsonable_encoder(CUSTOM_RESPONSE)
    )
    assert response_data == CUSTOM_RESPONSE
    # validating no `zombie` traces exist
    assert not trace_factory.traces


@pytest.mark.asyncio
async def test_fastapi_custom_status_code_overridden(trace_transport, fastapi_app):
    """custom status code test - status code overridden by returned Response """
    path = OVERRIDDEN_CUSTOM_STATUS_CODE_PATH
    request_path = f'{path}?x=testval'
    async with AsyncClient(app=fastapi_app, base_url="http://test") as ac:
        response = await ac.get(request_path)
    response_data = response.json()
    runner = trace_transport.last_trace.events[0]
    assert isinstance(runner, FastapiRunner)
    assert runner.resource['name'].startswith('127.0.0.1')
    assert runner.resource['metadata']['Path'] == path
    assert runner.resource['metadata']['status_code'] == DEFAULT_STATUS_CODE
    assert runner.resource['metadata']['Query Params'] == { 'x': 'testval'}
    expected_response_data = _get_response_data(RETURN_VALUE)
    assert runner.resource['metadata']['Response Data'] == (
        expected_response_data
    )
    assert runner.resource['metadata']['Query Params'] == { 'x': 'testval'}
    assert response_data == expected_response_data
    # validating no `zombie` traces exist
    assert not trace_factory.traces


@pytest.mark.asyncio
async def test_fastapi_given_request(trace_transport, fastapi_app):
    """handler with a request parameter test."""
    request_path = f'{REQUEST_OBJ_PATH}?x=testval'
    async with AsyncClient(app=fastapi_app, base_url="http://test") as ac:
        response = await ac.post(request_path, json=TEST_POST_DATA)
    response_data = response.json()
    runner = trace_transport.last_trace.events[0]
    assert isinstance(runner, FastapiRunner)
    assert runner.resource['name'].startswith('127.0.0.1')
    assert runner.resource['metadata']['Path'] == REQUEST_OBJ_PATH
    assert runner.resource['metadata']['status_code'] == DEFAULT_STATUS_CODE
    expected_response_data = _get_response_data(RETURN_VALUE)
    assert runner.resource['metadata']['Response Data'] == (
        expected_response_data
    )
    assert runner.resource['metadata']['Query Params'] == { 'x': 'testval'}
    assert response_data == expected_response_data
    # validating no `zombie` traces exist
    assert not trace_factory.traces


@pytest.mark.asyncio
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
    assert runner.resource['metadata']['status_code'] == DEFAULT_STATUS_CODE
    expected_response_data = _get_response_data(ROUTER_RETURN_VALUE)
    assert runner.resource['metadata']['Response Data'] == (
        expected_response_data
    )
    assert response_data == expected_response_data


@pytest.mark.asyncio
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
    assert "status_code" not in runner.resource['metadata']
    # validating no `zombie` traces exist
    assert not trace_factory.traces


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
    assert runner.resource['metadata']['status_code'] == DEFAULT_STATUS_CODE
    expected_response_data = _get_response_data(path)
    assert runner.resource['metadata']['Response Data'] == (
        expected_response_data
    )
    assert response_data == expected_response_data


@pytest.mark.asyncio
async def test_fastapi_multiple_requests(trace_transport, fastapi_app):
    """ Multiple requests test """
    for _ in range(3):
        await asyncio.gather(
            _send_request(fastapi_app, "a", trace_transport),
            _send_request(fastapi_app, "b", trace_transport)
        )
    # validating no `zombie` traces exist
    assert not trace_factory.traces


async def _send_async_request(app, path):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        return await ac.get(path)


def test_fastapi_multiple_threads_route(trace_transport, fastapi_app):
    """
    Tests request to a route, which invokes multiple threads.
    Validating no `zombie` traces exist (fromn the callback invoked threads)
    """
    loop = None
    try:
        loop = asyncio.new_event_loop()
        response = loop.run_until_complete(
            _send_async_request(
                fastapi_app,
                f"{MULTIPLE_THREADS_ROUTE}?x=testval"
            )
        )
    finally:
        if loop:
            loop.close()
    response_data = response.json()
    # expects only 1 event. The new threads events shouldn't belong this trace
    assert len(trace_transport.last_trace.events) == 1
    runner = trace_transport.last_trace.events[0]
    assert isinstance(runner, FastapiRunner)
    assert runner.resource['name'].startswith('127.0.0.1')
    assert runner.resource['metadata']['Path'] == MULTIPLE_THREADS_ROUTE
    assert runner.resource['metadata']['status_code'] == DEFAULT_STATUS_CODE
    expected_response_data = _get_response_data(MULTIPLE_THREADS_RETURN_VALUE)
    assert runner.resource['metadata']['Response Data'] == (
        expected_response_data
    )
    assert runner.resource['metadata']['Query Params'] == { 'x': 'testval'}
    assert response_data == expected_response_data
    # validating no `zombie` traces exist
    assert not trace_factory.traces
