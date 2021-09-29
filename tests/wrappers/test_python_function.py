import sys
import mock
import pytest
from collections import namedtuple
from epsagon import trace_factory
import epsagon.constants

trace_mock = mock.MagicMock()

Frame = namedtuple('Frame', 'f_locals')
FrameInfo = namedtuple(
    'FrameInfo',
    'frame, filename, lineno, function, code_context, index'
)

def setup_function(func):
    trace_factory.use_single_trace = True


def test_function_wrapper_sanity(trace_transport, ):
    retval = 'success'

    @epsagon.python_wrapper(name='test-func')
    def wrapped_function(event, context):
        return retval

    assert wrapped_function('a', 'b') == 'success'

    assert len(trace_transport.last_trace.events) == 1

    event = trace_transport.last_trace.events[0]
    assert event.resource['type'] == 'python_function'
    assert event.resource['name'] == 'test-func'
    assert event.resource['metadata']['python.function.return_value'] == retval
    assert event.error_code == 0


def test_function_wrapper_function_exception(trace_transport):
    @epsagon.python_wrapper()
    def wrapped_function(event, context):
        raise TypeError('test')

    with pytest.raises(TypeError):
        wrapped_function('a', 'b')

    assert len(trace_transport.last_trace.events) == 1

    event = trace_transport.last_trace.events[0]
    assert event.exception['type'] == 'TypeError'
    assert event.resource['metadata']['python.function.return_value'] is None
    assert not trace_transport.last_trace.exceptions


@mock.patch(
    'epsagon.trace.trace_factory.get_or_create_trace',
    side_effect=lambda: trace_mock
)
def test_python_wrapper_python_runner_factory_failed(_):
    @epsagon.python_wrapper
    def wrapped_function(event, context):
        return 'success'

    with mock.patch(
            'epsagon.runners.python_function.PythonRunner',
            side_effect=TypeError()
    ):
        assert wrapped_function('a', 'b') == 'success'

    trace_mock.prepare.assert_called_once()
    trace_mock.send_traces.assert_not_called()
    trace_mock.set_runner.assert_not_called()
    trace_mock.reset_mock()


@mock.patch(
    'inspect.trace',
    return_value=[FrameInfo(
        frame=Frame(f_locals={'param': 'value'}),
        filename='filename',
        lineno=1,
        function='function',
        code_context=['code_context'],
        index=0,
    )]
)
def test_function_wrapper_function_exception_frames(_, trace_transport):
    @epsagon.python_wrapper()
    def wrapped_function():
        raise TypeError('test')

    with pytest.raises(TypeError):
        wrapped_function()

    assert len(trace_transport.last_trace.events) == 1
    event = trace_transport.last_trace.events[0]
    if sys.version_info.major == 3:
        assert event.exception['frames'] ==  {
            'filename/function/1': {'param': 'value'}
        }

