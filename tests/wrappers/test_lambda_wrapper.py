import json
import mock
import pytest
import warnings
import epsagon.wrappers.aws_lambda
from epsagon.wrappers.return_value import FAILED_TO_SERIALIZE_MESSAGE
from epsagon.runners.aws_lambda import LambdaRunner, StepLambdaRunner
import epsagon.constants
from .common import get_tracer_patch_kwargs


def setup_function(func):
    epsagon.constants.COLD_START = True


def _get_runner_event(trace_mock, runner_type=LambdaRunner):
    for args, _ in trace_mock.set_runner.call_args_list:
        event = args[0]
        if isinstance(event, runner_type):
            return event

    assert False, "No runner found"


CONTEXT_STUB = type(
    'Context',
    (object,),
    {
        'aws_request_id': 'test_request_id',
        'function_name': 'TestFunction',
        'log_stream_name': 'test_stream',
        'log_group_name': 'test_group',
        'function_version': 'test_version',
        'memory_limit_in_mb': '1024',
        'invoked_function_arn': 'arn:aws:lambda:us-east-1:123456789012:function:TestFunction'
     }
)


# aws_lambda tests

@mock.patch.object(LambdaRunner, 'set_exception')
@mock.patch(
    'epsagon.trace.tracer',
    **get_tracer_patch_kwargs()
)
@mock.patch(
    'epsagon.triggers.aws_lambda.LambdaTriggerFactory.factory',
    side_effect=['trigger']
)
def test_lambda_wrapper_sanity(
    trigger_factory_mock,
    trace_mock,
    set_exception_mock
):
    retval = 'success'

    @epsagon.wrappers.aws_lambda.lambda_wrapper
    def wrapped_lambda(event, context):
        return 'success'

    assert wrapped_lambda('a', CONTEXT_STUB) == 'success'
    trace_mock.prepare.assert_called()
    runner = _get_runner_event(trace_mock)

    trigger_factory_mock.assert_called()
    set_exception_mock.assert_not_called()

    trace_mock.set_timeout_handler.assert_called()

    trace_mock.send_traces.assert_called()
    trace_mock.add_exception.assert_not_called()

    assert not epsagon.constants.COLD_START
    assert runner.resource['metadata']['return_value'] == json.dumps(retval)


@mock.patch(
    'epsagon.trace.tracer',
    **get_tracer_patch_kwargs()
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
            wrapped_lambda('a', CONTEXT_STUB)

    trigger_factory_mock.assert_called()

    lambda_runner_mock.set_exception.assert_called()

    trace_mock.prepare.assert_called()
    trace_mock.add_event.assert_called()
    trace_mock.send_traces.assert_called()
    trace_mock.add_exception.assert_not_called()

    assert not epsagon.constants.COLD_START


@mock.patch(
    'epsagon.trace.tracer',
    **get_tracer_patch_kwargs()
)
def test_lambda_wrapper_lambda_exception_args(trace_mock):
    """
    Tests that when user invoking Lambda's handler manually with kwargs,
    trace won't be sent, and return value is ok.
    """
    @epsagon.wrappers.aws_lambda.lambda_wrapper
    def wrapped_lambda(event, context):
        return 'success'

    lambda_runner_mock = mock.MagicMock(set_exception=mock.MagicMock())
    with mock.patch(
        'epsagon.runners.aws_lambda.LambdaRunner',
        side_effect=[lambda_runner_mock]
    ):
        assert wrapped_lambda(event='a', context='b') == 'success'

    trace_mock.prepare.assert_called()
    trace_mock.add_event.assert_not_called()
    trace_mock.send_traces.assert_not_called()
    trace_mock.add_exception.assert_not_called()
    assert epsagon.constants.COLD_START


@mock.patch(
    'epsagon.trace.tracer',
    **get_tracer_patch_kwargs()
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
        wrapped_lambda('a', CONTEXT_STUB)

    trigger_factory_mock.assert_called()

    lambda_runner_mock.set_exception.assert_not_called()

    trace_mock.prepare.assert_called()
    trace_mock.set_runner.assert_called()
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
            assert wrapped_lambda('a', CONTEXT_STUB) == 'success'
        assert len(w) == 1

    tracer_mock.prepare.assert_called()
    wrap_python_function_wrapper.assert_called()


@mock.patch(
    'epsagon.trace.tracer',
    **get_tracer_patch_kwargs()
)
def test_lambda_wrapper_invalid_return_value(trace_mock):
    @epsagon.wrappers.aws_lambda.lambda_wrapper
    def wrapped_function(event, context):
        return pytest # Not json-serializable

    assert wrapped_function('a', CONTEXT_STUB) == pytest
    trace_mock.prepare.assert_called_once()
    runner = _get_runner_event(trace_mock)

    trace_mock.send_traces.assert_called_once()
    trace_mock.add_exception.assert_not_called()

    assert (
        runner.resource['metadata']['return_value'] ==
        FAILED_TO_SERIALIZE_MESSAGE
    )

# step_lambda_wrapper tests

@mock.patch.object(StepLambdaRunner, 'set_exception')
@mock.patch(
    'epsagon.trace.tracer',
    **get_tracer_patch_kwargs()
)
@mock.patch(
    'epsagon.triggers.aws_lambda.LambdaTriggerFactory.factory',
    side_effect=['trigger']
)
def test_step_lambda_wrapper_sanity_first_step(
    trigger_factory_mock,
    trace_mock,
    set_exception_mock
):
    retval = {'result': 'success'}

    @epsagon.wrappers.aws_lambda.step_lambda_wrapper
    def wrapped_lambda(event, context):
        return retval

    result = wrapped_lambda('a', CONTEXT_STUB)
    assert ('result', 'success', ) in result.items()
    assert 'Epsagon' in result
    assert ('step_num', 0, ) in result['Epsagon'].items()
    assert 'id' in result['Epsagon']

    trigger_factory_mock.assert_called()
    set_exception_mock.assert_not_called()

    trace_mock.prepare.assert_called()
    trace_mock.add_event.assert_called()
    trace_mock.set_runner.assert_called()
    trace_mock.set_timeout_handler.assert_called()
    runner = _get_runner_event(trace_mock, runner_type=StepLambdaRunner)
    trace_mock.send_traces.assert_called()
    trace_mock.add_exception.assert_not_called()

    assert not epsagon.constants.COLD_START
    assert runner.resource['metadata']['return_value'] == json.dumps(retval)


@mock.patch(
    'epsagon.trace.tracer',
    **get_tracer_patch_kwargs()
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
        result = wrapped_lambda(
            {'a': 'a', 'Epsagon': {'step_num': 1, 'id': 1}},
            CONTEXT_STUB
        )
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
    **get_tracer_patch_kwargs()
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
        assert wrapped_lambda(
            {'a': 'a', 'Epsagon': {'step_num': 1, 'id': 1}},
            CONTEXT_STUB
        ) == 'success'

    trigger_factory_mock.assert_called()
    lambda_runner_mock.set_exception.assert_not_called()

    trace_mock.prepare.assert_called()
    trace_mock.add_event.assert_called()
    trace_mock.send_traces.assert_called()
    trace_mock.add_exception.assert_not_called()

    assert not epsagon.constants.COLD_START


@mock.patch(
    'epsagon.trace.tracer',
    **get_tracer_patch_kwargs()
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
            wrapped_lambda('a', CONTEXT_STUB)

    trigger_factory_mock.assert_called()

    lambda_runner_mock.set_exception.assert_called()

    trace_mock.prepare.assert_called()
    trace_mock.add_event.assert_called()
    trace_mock.send_traces.assert_called()
    trace_mock.add_exception.assert_not_called()

    assert not epsagon.constants.COLD_START


@mock.patch(
    'epsagon.trace.tracer',
    **get_tracer_patch_kwargs()
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
        wrapped_lambda('a', CONTEXT_STUB)

    trigger_factory_mock.assert_called()

    lambda_runner_mock.set_exception.assert_not_called()

    trace_mock.prepare.assert_called()
    trace_mock.set_runner.assert_called()
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
            assert wrapped_lambda('a', CONTEXT_STUB) == 'success'
        assert len(w) == 1

    tracer_mock.prepare.assert_called()
    wrap_python_function_wrapper.assert_called()


@mock.patch(
    'epsagon.trace.tracer',
    **get_tracer_patch_kwargs()
)
def test_step_lambda_wrapper_invalid_return_value(trace_mock):
    @epsagon.wrappers.aws_lambda.step_lambda_wrapper
    def wrapped_function(event, context):
        return pytest # Not json-serializable

    assert wrapped_function('a', CONTEXT_STUB) == pytest
    trace_mock.prepare.assert_called_once()
    runner = _get_runner_event(trace_mock, runner_type=StepLambdaRunner)

    trace_mock.send_traces.assert_called_once()
    trace_mock.add_exception.assert_not_called()

    assert (
        runner.resource['metadata']['return_value'] ==
        FAILED_TO_SERIALIZE_MESSAGE
    )
