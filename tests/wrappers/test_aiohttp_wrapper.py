import asynctest
from aiohttp import web
from epsagon.common import ErrorCode
from epsagon.wrappers.aiohttp import AiohttpMiddleware
from epsagon.runners.aiohttp import AiohttpRunner


# Setting demo aiohttp handlers
RETURN_VALUE = 'a'
async def handle(request):
    return web.Response(body=RETURN_VALUE)

async def handle_error(request):
    raise Exception('test')


def create_app(loop):
    app = web.Application(loop=loop, middlewares=[AiohttpMiddleware])
    app.router.add_route('GET', '/', handle)
    app.router.add_route('GET', '/err', handle_error)
    return app


@asynctest.patch('epsagon.trace.trace_factory.use_async_tracer')
async def test_aiohttp_sanity(_, trace_transport, aiohttp_client):
    """Sanity test."""
    client = await aiohttp_client(create_app)
    response = await client.get('/')
    text = await response.text()
    runner = trace_transport.last_trace.events[0]
    assert isinstance(runner, AiohttpRunner)
    assert runner.resource['name'].startswith('127.0.0.1')
    assert runner.resource['metadata']['Path'] == '/'
    assert runner.resource['metadata']['Response Data'] == RETURN_VALUE
    assert text == RETURN_VALUE


@asynctest.patch('epsagon.trace.trace_factory.use_async_tracer')
async def test_aiohttp_exception(_, trace_transport, aiohttp_client):
    """Test when the handler got an exception."""
    client = await aiohttp_client(create_app)

    try:
        await client.get('/err')
    except:
        pass

    runner = trace_transport.last_trace.events[0]
    assert runner.error_code == ErrorCode.EXCEPTION
    assert runner.exception['type'] == 'Exception'
    assert runner.exception['message'] == 'test'
