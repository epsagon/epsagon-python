import mock
import pytest
import warnings
import epsagon.wrappers.aws_lambda
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
@mock.patch(
    'epsagon.triggers.aws_lambda.LambdaTriggerFactory.factory',
    side_effect=['trigger']
)
def test_lambda_wrapper_sanity(trigger_factory_mock, trace_mock):
    @epsagon.wrappers.aws_lambda.lambda_wrapper
    def wrapped_lambda(event, context):
        return 'success'

    lambda_runner_mock = mock.MagicMock(set_exception=mock.MagicMock())
    with mock.patch(
        'epsagon.runners.aws_lambda.LambdaRunner',
         side_effect=[lambda_runner_mock]
    ):
        assert wrapped_lambda('a', 'b') == 'success'

    trigger_factory_mock.assert_called()
    lambda_runner_mock.set_exception.assert_not_called()

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
@mock.patch(
    'epsagon.triggers.aws_lambda.LambdaTriggerFactory.factory',
    side_effect=['trigger']
)
def test_lambda_wrapper_lambda_exception(trigger_factory_mock, trace_mock):
    @epsagon.wrappers.aws_lambda.lambda_wrapper
    def wrapped_lambda(event, context):
        raise TypeError('test')

    lambda_runner_mock = mock.MagicMock(set_exception=mock.MagicMock())
    with mock.patch('epsagon.runners.aws_lambda.LambdaRunner', side_effect=[lambda_runner_mock]):
        with pytest.raises(TypeError):
            wrapped_lambda('a', 'b')

    trigger_factory_mock.assert_called()

    lambda_runner_mock.set_exception.assert_called()

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
@mock.patch(
    'epsagon.triggers.aws_lambda.LambdaTriggerFactory.factory',
    side_effect=TypeError()
)
def test_lambda_wrapper_trigger_exception(trigger_factory_mock, trace_mock):
    @epsagon.wrappers.aws_lambda.lambda_wrapper
    def wrapped_lambda(event, context):
        pass

    lambda_runner_mock = mock.MagicMock(set_exception=mock.MagicMock())
    with mock.patch(
        'epsagon.runners.aws_lambda.LambdaRunner',
        side_effect=[lambda_runner_mock]
    ):
        wrapped_lambda('a', 'b')

    trigger_factory_mock.assert_called()

    lambda_runner_mock.set_exception.assert_not_called()

    trace_mock.prepare.assert_called()
    trace_mock.add_event.assert_called()
    trace_mock.send_traces.assert_called()
    trace_mock.add_exception.assert_called()

    assert not epsagon.constants.COLD_START


@mock.patch(
    'epsagon.wrappers.python_function.wrap_python_function',
    side_effect=['success']
)
def test_lambda_wrapper_none_context(wrap_python_function_mock):
    @epsagon.wrappers.aws_lambda.lambda_wrapper
    def wrapped_lambda(event, context):
        # In this test we validate wrap_python_function return value, and the
        # RV doesn't matter here. It is tested on wrap_python_function tests
        return 'success'

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always')
        lambda_runner_mock = mock.MagicMock(set_exception=mock.MagicMock())
        with mock.patch(
                'epsagon.runners.aws_lambda.LambdaRunner',
                side_effect=[lambda_runner_mock]
        ):
            assert wrapped_lambda('a', None) == 'success'
        assert len(w) == 1

    wrap_python_function_mock.assert_called()


@mock.patch(
    'epsagon.trace.tracer',
    prepare=mock.MagicMock(),
    send_traces=mock.MagicMock(),
    events=[],
    add_events=mock.MagicMock(),
    add_exception=mock.MagicMock()
)
@mock.patch(
    'epsagon.triggers.aws_lambda.LambdaTriggerFactory.factory',
    side_effect=['trigger']
)
@mock.patch(
    'epsagon.runners.python_function.PythonRunner',
)
def test_lambda_wrapper_lambda_runner_factory_failed(python_runner_mock, trigger_factory_mock, trace_mock):
    @epsagon.wrappers.aws_lambda.lambda_wrapper
    def wrapped_lambda(event, context):
        return 'success'

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always')
        with mock.patch(
                'epsagon.runners.aws_lambda.LambdaRunner',
                side_effect=TypeError()
        ):
            assert wrapped_lambda('a', 'b') == 'success'
        assert len(w) == 1

    python_runner_mock.assert_called()
    trigger_factory_mock.assert_called()

    trace_mock.prepare.assert_called_once()
    assert trace_mock.add_event.call_count == 2
    trace_mock.send_traces.assert_called()
    trace_mock.add_exception.assert_called_once()

    assert not epsagon.constants.COLD_START

@mock.patch(
    'epsagon.trace.tracer',
    prepare=mock.MagicMock(),
    send_traces=mock.MagicMock(),
    events=[],
    add_events=mock.MagicMock(),
    add_exception=mock.MagicMock()
)
@mock.patch(
    'epsagon.triggers.aws_lambda.LambdaTriggerFactory.factory',
    side_effect=['trigger']
)
@mock.patch(
    'epsagon.runners.python_function.PythonRunner',
    side_effect=TypeError()
)
def test_lambda_wrapper_all_runner_factory_failed(python_runner_mock, trigger_factory_mock, trace_mock):
    @epsagon.wrappers.aws_lambda.lambda_wrapper
    def wrapped_lambda(event, context):
        return 'success'

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always')
        with mock.patch(
                'epsagon.runners.aws_lambda.LambdaRunner',
                side_effect=TypeError()
        ):
            assert wrapped_lambda('a', 'b') == 'success'
        assert len(w) == 1

    python_runner_mock.assert_called()

    assert trace_mock.add_event.call_count == 1
    trace_mock.send_traces.assert_not_called()
    trace_mock.add_exception.assert_called_once()

    # not asserting COLD_START here because the pythonRunner is handling it
    # Will be validated on pythonRunner tests

