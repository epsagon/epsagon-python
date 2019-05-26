import json
import threading
import mock
import pytest
import epsagon.wrappers.python_function
from epsagon.trace import trace_factory
from epsagon.wrappers.return_value import FAILED_TO_SERIALIZE_MESSAGE
import epsagon.runners.python_function
import epsagon.constants
from .common import get_tracer_patch_kwargs

trace_mock = mock.MagicMock()


def setup_function(func):
    trace_mock.configure_mock(**get_tracer_patch_kwargs())
    if trace_factory.use_single_trace:
        trace_factory.singleton_trace = trace_mock
    else:
        trace_factory.traces[threading.currentThread().ident] = trace_mock
    epsagon.constants.COLD_START = True


@mock.patch(
    'epsagon.trace.trace_factory.get_or_create_trace',
    side_effect=lambda: trace_mock
)
def test_function_wrapper_sanity(_, ):
    retval = 'success'

    @epsagon.wrappers.python_function.python_wrapper
    def wrapped_function(event, context):
        return retval

    assert wrapped_function('a', 'b') == 'success'
    trace_mock.prepare.assert_called_once()
    trace_mock.set_runner.assert_called_once()
    (event,), _ = trace_mock.set_runner.call_args
    assert isinstance(event, epsagon.runners.python_function.PythonRunner)

    trace_mock.send_traces.assert_called_once()
    trace_mock.add_exception.assert_not_called()

    assert not epsagon.constants.COLD_START
    assert event.resource['metadata']['return_value'] == json.dumps(retval)


@mock.patch.object(
    epsagon.runners.python_function.PythonRunner,
    'set_exception'
)
@mock.patch(
    'epsagon.trace.trace_factory.get_or_create_trace',
    side_effect=lambda: trace_mock)
def test_function_wrapper_function_exception(_, set_exception_mock):
    @epsagon.wrappers.python_function.python_wrapper
    def wrapped_function(event, context):
        raise TypeError('test')

    with pytest.raises(TypeError):
        wrapped_function('a', 'b')

    # function_runner_mock.set_exception.assert_called()
    set_exception_mock.assert_called_once()

    trace_mock.prepare.assert_called_once()
    trace_mock.set_runner.assert_called_once()

    (event,), _ = trace_mock.set_runner.call_args
    assert isinstance(event, epsagon.runners.python_function.PythonRunner)

    trace_mock.send_traces.assert_called_once()
    trace_mock.add_exception.assert_not_called()

    assert not epsagon.constants.COLD_START
    assert event.resource['metadata']['return_value'] == json.dumps(None)


@mock.patch(
    'epsagon.trace.trace_factory.get_or_create_trace',
    side_effect=lambda: trace_mock
)
def test_python_wrapper_python_runner_factory_failed(_):
    @epsagon.wrappers.python_function.python_wrapper
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


@mock.patch(
    'epsagon.trace.trace_factory.get_or_create_trace',
    side_effect=lambda: trace_mock
)
def test_python_wrapper_invalid_return_value(_):
    @epsagon.wrappers.python_function.python_wrapper
    def wrapped_function(event, context):
        return pytest  # Not json-serializable

    assert wrapped_function('a', 'b') == pytest

    trace_mock.prepare.assert_called_once()
    trace_mock.set_runner.assert_called_once()
    (event,), _ = trace_mock.set_runner.call_args
    assert isinstance(event, epsagon.runners.python_function.PythonRunner)

    trace_mock.send_traces.assert_called_once()
    trace_mock.add_exception.assert_not_called()

    assert not epsagon.constants.COLD_START
    assert (
            event.resource['metadata']['return_value'] ==
            FAILED_TO_SERIALIZE_MESSAGE
    )


@mock.patch(
    'epsagon.trace.trace_factory.get_or_create_trace',
    side_effect=lambda: trace_mock
)
def test_python_wrapper_single_thread(_):
    retval = 'success'

    @epsagon.wrappers.python_function.python_wrapper
    def wrapped_function(event, context):
        return retval

    assert wrapped_function('a', 'b') == retval
    assert trace_factory.use_single_trace
