import mock
import epsagon.wrappers.python_function
from epsagon.trace import trace_factory
import epsagon.runners.python_function
import epsagon.constants
import logging
from ..wrappers.common import get_tracer_patch_kwargs

trace_mock = mock.MagicMock()


def setup_function(func):
    trace_mock.configure_mock(**get_tracer_patch_kwargs())
    trace_factory.singleton_trace = trace_mock
    trace_factory.use_single_trace = True
    epsagon.constants.COLD_START = True


def test_logging_exception_capture():
    retval = 'success'

    @epsagon.wrappers.python_function.python_wrapper
    def wrapped_function(event, context):
        logging.exception('test')
        return retval

    assert wrapped_function('a', 'b') == retval
    trace_mock.set_error.assert_called_with('test', None)


def test_logging_exception_capture_with_args():
    retval = 'success'

    @epsagon.wrappers.python_function.python_wrapper
    def wrapped_function(event, context):
        logging.exception('test %s %s', 'test', 'test')
        return retval

    assert wrapped_function('a', 'b') == retval
    trace_mock.set_error.assert_called_with('test test test', None)
