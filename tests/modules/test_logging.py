import epsagon.wrappers.python_function
from epsagon.trace import trace_factory
import epsagon.runners.python_function
import epsagon.constants
import logging


def setup_function(func):
    trace_factory.use_single_trace = True
    epsagon.constants.COLD_START = True


def test_logging_exception_capture(trace_transport):
    retval = 'success'

    @epsagon.wrappers.python_function.python_wrapper
    def wrapped_function(event, context):
        logging.exception('test')
        return retval

    assert wrapped_function('a', 'b') == retval

    exception = trace_transport.last_trace.events[0].exception
    assert exception['type'] == 'EpsagonException'
    assert exception['message'] == 'test'


def test_logging_exception_capture_with_args(trace_transport):
    retval = 'success'

    @epsagon.wrappers.python_function.python_wrapper
    def wrapped_function(event, context):
        logging.exception('test %s %s', 'test', 'test')
        return retval

    assert wrapped_function('a', 'b') == retval

    exception = trace_transport.last_trace.events[0].exception
    assert exception['type'] == 'EpsagonException'
    assert exception['message'] == 'test test test'
