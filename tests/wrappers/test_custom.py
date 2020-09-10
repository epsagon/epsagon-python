import mock
import json
import itertools
import epsagon.constants
from epsagon import trace_factory


def setup_function(func):
    trace_factory.use_async_tracer = False


@mock.patch(
    'time.time',
    side_effect=itertools.count(start=1)
)
def test_function_wrapper_sanity(_, trace_transport):
    retval = 'success'

    @epsagon.measure
    def measured_function():
        return retval

    @epsagon.python_wrapper(name='test-func')
    def wrapped_function():
        measured_function()
        return retval

    assert wrapped_function() == retval
    labels = json.loads(trace_transport.last_trace.events[0].resource['metadata']['labels'])
    assert labels['measured_function_duration'] == 1
