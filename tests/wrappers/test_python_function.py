import mock
import pytest
import epsagon.wrappers.python_function
import epsagon.constants

def setup_function(func):
    epsagon.constants.COLD_START = True


@mock.patch(
    'epsagon.trace.tracer',
    prepare=mock.MagicMock(),
    send_traces=mock.MagicMock(),
    events=[],
    add_events=mock.MagicMock(),
    add_exception=mock.MagicMock()
)
def test_function_wrapper_sanity(trace_mock):
    @epsagon.wrappers.python_function.python_wrapper
    def wrapped_function(event, context):
        return 'success'

    runner_mock = mock.MagicMock(set_exception=mock.MagicMock())
    with mock.patch(
            'epsagon.runners.python_function.PythonRunner',
            side_effect=[runner_mock]
    ):
        assert wrapped_function('a', 'b') == 'success'

    runner_mock.set_exception.assert_not_called()

    trace_mock.prepare.assert_called()
    trace_mock.add_event.assert_called()
    trace_mock.send_traces.assert_called()
    trace_mock.add_exception.assert_not_called()

    assert not epsagon.constants.COLD_START


@mock.patch(
    'epsagon.trace.tracer',
    prepare=mock.MagicMock(),
    send_traces=mock.MagicMock(),
    events=[],
    add_events=mock.MagicMock(),
    add_exception=mock.MagicMock()
)
def test_function_wrapper_function_exception(trace_mock):
    @epsagon.wrappers.python_function.python_wrapper
    def wrapped_function(event, context):
        raise TypeError('test')

    function_runner_mock = mock.MagicMock(set_exception=mock.MagicMock())
    with mock.patch(
        'epsagon.runners.python_function.PythonRunner',
        side_effect=[function_runner_mock]
    ):
        with pytest.raises(TypeError):
            wrapped_function('a', 'b')

    function_runner_mock.set_exception.assert_called()

    trace_mock.prepare.assert_called()
    trace_mock.add_event.assert_called()
    trace_mock.send_traces.assert_called()
    trace_mock.add_exception.assert_not_called()

    assert not epsagon.constants.COLD_START


@mock.patch(
    'epsagon.trace.tracer',
    prepare=mock.MagicMock(),
    send_traces=mock.MagicMock(),
    events=[],
    add_events=mock.MagicMock(),
    add_exception=mock.MagicMock()
)
def test_python_wrapper_python_runner_factory_failed(trace_mock):
    @epsagon.wrappers.python_function.python_wrapper
    def wrapped_function(event, context):
        return 'success'

    with mock.patch(
            'epsagon.runners.python_function.PythonRunner',
            side_effect=TypeError()
    ):
        assert wrapped_function('a', 'b') == 'success'

    trace_mock.prepare.assert_called()
    trace_mock.send_traces.assert_not_called()
    trace_mock.add_event.assert_not_called()


