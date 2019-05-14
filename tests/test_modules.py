import mock

from epsagon.modules.botocore import _wrapper as _botocore_wrapper
from epsagon.modules.grpc import _wrapper as _grpc_wrapper
from epsagon.modules.requests import _wrapper as _request_wrapper
from epsagon.modules.pymongo import _wrapper as _pymongo_wrapper
from epsagon.trace import trace_factory

EXCEPTION_MESSAGE = 'Test exception'
EXCEPTION_TYPE = RuntimeError


def raise_exception(*args):
    raise EXCEPTION_TYPE(EXCEPTION_MESSAGE)


def _test(func):
    func(lambda: None, [], [], {})
    trace = trace_factory.get_or_create_trace()
    assert len(trace.exceptions) == 1
    assert trace.exceptions[0]['message'] == EXCEPTION_MESSAGE
    assert trace.exceptions[0]['type'] == str(EXCEPTION_TYPE)
    assert 'time' in trace.exceptions[0].keys()
    assert len(trace.exceptions[0]['traceback']) > 0


def setup_function(function):
    """Setup function that resets the tracer's exceptions list.
    """
    trace_factory.get_or_create_trace().exceptions = []


@mock.patch(
    'epsagon.events.requests.RequestsEventFactory.create_event',
    side_effect=raise_exception
)
def test_request_wrapper_failsafe(_):
    """Validates that the request wrapper is not raising any exception to
    the user."""
    _test(_request_wrapper)


@mock.patch('epsagon.events.pymongo.PyMongoEventFactory.create_event',
            side_effect=raise_exception)
def test_pymongo_wrapper_failsafe(_):
    """Validates that the pymongo wrapper is not raising any exception to
    the user."""
    _test(_pymongo_wrapper)


@mock.patch('epsagon.events.grpc.GRPCEventFactory.create_event',
            side_effect=raise_exception)
def test_grpc_wrapper_failsafe(_):
    """Validates that the GRPC wrapper is not raising any exception to
    the user."""
    _test(_grpc_wrapper)


@mock.patch('epsagon.events.botocore.BotocoreEventFactory.create_event',
            side_effect=raise_exception)
def test_botocore_wrapper_failsafe(_):
    """Validates that the botocore wrapper is not raising any exception to
    the user."""
    _test(_botocore_wrapper)
