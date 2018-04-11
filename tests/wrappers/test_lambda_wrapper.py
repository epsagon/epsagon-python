import mock
import pytest
import warnings
import epsagon.wrappers.aws_lambda
import epsagon.constants


def setup_function(func):
    epsagon.constants.COLD_START = True


# lambda_wrapper tests
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
    with mock.patch(
        'epsagon.runners.aws_lambda.LambdaRunner',
        side_effect=[lambda_runner_mock]
    ):
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
    'epsagon.trace.tracer',
    prepare=mock.MagicMock(),
)
@mock.patch(
    'epsagon.wrappers.python_function.wrap_python_function',
    side_effect=['success']
)
def test_lambda_wrapper_none_context(wrap_python_function_wrapper, tracer_mock):
    @epsagon.wrappers.aws_lambda.lambda_wrapper
    def wrapped_lambda(event, context):
        # Doesn't matter, we are mocking wrap_python_function
        return 'something'

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always')
        lambda_runner_mock = mock.MagicMock(set_exception=mock.MagicMock())
        with mock.patch(
                'epsagon.runners.aws_lambda.LambdaRunner',
                side_effect=TypeError()
        ):
            assert wrapped_lambda('a', None) == 'success'
        assert len(w) == 1

    tracer_mock.prepare.assert_called()
    wrap_python_function_wrapper.assert_called()


@mock.patch(
    'epsagon.trace.tracer',
    prepare=mock.MagicMock(),
)
@mock.patch(
    'epsagon.wrappers.python_function.wrap_python_function',
    side_effect=['success']
)
def test_lambda_wrapper_lambda_runner_factory_failed(wrap_python_function_wrapper, tracer_mock):
    @epsagon.wrappers.aws_lambda.lambda_wrapper
    def wrapped_lambda(event, context):
        # Doesn't matter, we are mocking wrap_python_function
        return 'something'

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always')
        with mock.patch(
                'epsagon.runners.aws_lambda.LambdaRunner',
                side_effect=TypeError()
        ):
            assert wrapped_lambda('a', 'b') == 'success'
        assert len(w) == 1

    tracer_mock.prepare.assert_called()
    wrap_python_function_wrapper.assert_called()


# step_lambda_wrapper tests
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
def test_step_lambda_wrapper_sanity_first_step(trigger_factory_mock, trace_mock):
    @epsagon.wrappers.aws_lambda.step_lambda_wrapper
    def wrapped_lambda(event, context):
        return {'result': 'success'}

    lambda_runner_mock = mock.MagicMock(set_exception=mock.MagicMock())
    with mock.patch(
            'epsagon.runners.aws_lambda.StepLambdaRunner',
            side_effect=[lambda_runner_mock]
    ):
        result = wrapped_lambda('a', 'b')
        assert ('result', 'success', ) in result.items()
        assert 'Epsagon' in result
        assert ('step_num', 0, ) in result['Epsagon'].items()
        assert 'id' in result['Epsagon']

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
def test_step_lambda_wrapper_sanity_not_first_step(trigger_factory_mock, trace_mock):
    @epsagon.wrappers.aws_lambda.step_lambda_wrapper
    def wrapped_lambda(event, context):
        return {'result': 'success'}

    lambda_runner_mock = mock.MagicMock(set_exception=mock.MagicMock())
    with mock.patch(
            'epsagon.runners.aws_lambda.StepLambdaRunner',
            side_effect=[lambda_runner_mock]
    ):
        result = wrapped_lambda({'a': 'a', 'Epsagon': {'step_num': 1, 'id': 1}}, 'b')
        assert ('result', 'success', ) in result.items()
        assert 'Epsagon' in result
        assert ('step_num', 2, ) in result['Epsagon'].items()
        assert 'id' in result['Epsagon']

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
def test_step_lambda_wrapper_wrapped_function_doesnt_return_object(trigger_factory_mock, trace_mock):
    @epsagon.wrappers.aws_lambda.step_lambda_wrapper
    def wrapped_lambda(event, context):
        return 'success'

    lambda_runner_mock = mock.MagicMock(set_exception=mock.MagicMock())
    with mock.patch(
            'epsagon.runners.aws_lambda.StepLambdaRunner',
            side_effect=[lambda_runner_mock]
    ):
        assert wrapped_lambda({'a': 'a', 'Epsagon': {'step_num': 1, 'id': 1}}, 'b') == 'success'

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
def test_step_lambda_wrapper_lambda_exception(trigger_factory_mock, trace_mock):
    @epsagon.wrappers.aws_lambda.step_lambda_wrapper
    def wrapped_lambda(event, context):
        raise TypeError('test')

    lambda_runner_mock = mock.MagicMock(set_exception=mock.MagicMock())
    with mock.patch(
            'epsagon.runners.aws_lambda.StepLambdaRunner',
            side_effect=[lambda_runner_mock]
    ):
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
def test_step_lambda_wrapper_trigger_exception(trigger_factory_mock, trace_mock):
    @epsagon.wrappers.aws_lambda.step_lambda_wrapper
    def wrapped_lambda(event, context):
        pass

    lambda_runner_mock = mock.MagicMock(set_exception=mock.MagicMock())
    with mock.patch(
            'epsagon.runners.aws_lambda.StepLambdaRunner',
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
    'epsagon.trace.tracer',
    prepare=mock.MagicMock(),
)
@mock.patch(
    'epsagon.wrappers.python_function.wrap_python_function',
    side_effect=['success']
)
def test_step_lambda_wrapper_none_context(wrap_python_function_wrapper, tracer_mock):
    @epsagon.wrappers.aws_lambda.step_lambda_wrapper
    def wrapped_lambda(event, context):
        # Doesn't matter, we are mocking wrap_python_function
        return 'something'

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always')
        lambda_runner_mock = mock.MagicMock(set_exception=mock.MagicMock())
        with mock.patch(
                'epsagon.runners.aws_lambda.StepLambdaRunner',
                side_effect=TypeError()
        ):
            assert wrapped_lambda('a', None) == 'success'
        assert len(w) == 1

    tracer_mock.prepare.assert_called()
    wrap_python_function_wrapper.assert_called()


@mock.patch(
    'epsagon.trace.tracer',
    prepare=mock.MagicMock(),
)
@mock.patch(
    'epsagon.wrappers.python_function.wrap_python_function',
    side_effect=['success']
)
def test_step_lambda_wrapper_lambda_runner_factory_failed(wrap_python_function_wrapper, tracer_mock):
    @epsagon.wrappers.aws_lambda.step_lambda_wrapper
    def wrapped_lambda(event, context):
        # Doesn't matter, we are mocking wrap_python_function
        return 'something'

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always')
        with mock.patch(
                'epsagon.runners.aws_lambda.StepLambdaRunner',
                side_effect=TypeError()
        ):
            assert wrapped_lambda('a', 'b') == 'success'
        assert len(w) == 1

    tracer_mock.prepare.assert_called()
    wrap_python_function_wrapper.assert_called()
