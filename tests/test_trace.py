from epsagon.trace import tracer

def setup_function(func):
    tracer.__init__()

def test_add_exception():
    stack_trace_format = 'stack trace %d'
    message_format = 'message %d'
    tested_exception_types = [
        ZeroDivisionError,
        RuntimeError,
        NameError,
        TypeError
    ]

    for i, exception_type in enumerate(tested_exception_types):
        try:
            raise exception_type(message_format % i)
        except ZeroDivisionError as e:
            tracer.add_exception(e, stack_trace_format %i)

    assert len(tracer.exceptions) == len(tested_exception_types)
    for i, exception_type in enumerate(tested_exception_types):
        current_exception = tracer.exceptions[i]
        assert current_exception['type'] == str(exception_type)
        assert current_exception['message'] == message_format % i
        assert current_exception['traceback'] == stack_trace_format % i
        assert type(current_exception['time']) == float




def test_prepare(self):

def test_initialize(self):

def test_load_from_dict(self):

def test_get_events(self):

def test_add_event(self):

def test_to_dict(self):

def test_send_traces(self):
