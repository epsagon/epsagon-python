import sys
import mock
import json
import requests
import warnings
import epsagon.trace
import epsagon.constants
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
        except exception_type as e:
            tracer.add_exception(e, stack_trace_format %i)

    assert len(tracer.exceptions) == len(tested_exception_types)
    for i, exception_type in enumerate(tested_exception_types):
        current_exception = tracer.exceptions[i]
        assert current_exception['type'] == str(exception_type)
        assert current_exception['message'] == message_format % i
        assert current_exception['traceback'] == stack_trace_format % i
        assert type(current_exception['time']) == float


def test_prepare():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always')
        tracer.prepare()
        assert tracer.events == []
        assert tracer.exceptions == []
        assert len(w) == 1

    tracer.events = ['test_event']
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always')
        tracer.prepare()
        assert tracer.events == []
        assert tracer.exceptions == []
        assert len(w) == 1

    tracer.events = ['test_event']
    with warnings.catch_warnings(record=True) as w:
        tracer.prepare()
        tracer.prepare() # this call should NOT trigger a warning
        assert tracer.events == []
        assert tracer.exceptions == []
        assert len(w) == 1


def test_initialize():
    app_name = 'app-name'
    token = 'token'
    tracer.initialize(app_name, token)
    assert tracer.app_name == app_name
    assert tracer.token == token

    tracer.initialize(app_name, '')
    assert tracer.app_name == app_name
    assert tracer.token == ''

    tracer.initialize('', '')
    assert tracer.app_name == ''
    assert tracer.token == ''


def test_load_from_dict():
    for i in range(2): # validate a new trace is created each time
        number_of_events = 10
        trace_data = {
            'app_name': 'app_name',
            'token': 'token',
            'version': 'version',
            'platform': 'platform',
            'events': range(number_of_events)
        }

        with mock.patch('epsagon.event.BaseEvent.load_from_dict', side_effect=(lambda x: x)):
            new_trace = epsagon.trace.Trace.load_from_dict(trace_data)
            assert new_trace.app_name == trace_data['app_name']
            assert new_trace.token == trace_data['token']
            assert new_trace.version == trace_data['version']
            assert new_trace.platform == trace_data['platform']
            assert new_trace.events == trace_data['events']
            assert new_trace.exceptions == {}


def test_load_from_dict_with_exceptions():
    for i in range(2): # validate a new trace is created each time
        number_of_events = 10
        trace_data = {
            'app_name': 'app_name',
            'token': 'token',
            'version': 'version',
            'platform': 'platform',
            'events': range(number_of_events),
            'exceptions': 'test_exceptions'
        }

        with mock.patch('epsagon.event.BaseEvent.load_from_dict', side_effect=(lambda x: x)):
            new_trace = epsagon.trace.Trace.load_from_dict(trace_data)
            assert new_trace.app_name == trace_data['app_name']
            assert new_trace.token == trace_data['token']
            assert new_trace.version == trace_data['version']
            assert new_trace.platform == trace_data['platform']
            assert new_trace.events == trace_data['events']
            assert new_trace.exceptions == trace_data['exceptions']


def test_add_event():
    class EventMock(object):
        def terminate(self):
            self.terminated = True

    event = EventMock()
    for i in range(10): # verify we can add more then 1 event
        tracer.add_event(event)
        assert event is tracer.events[i]
        assert event.terminated


def test_to_dict():
    class EventMock(object):
        def __init__(self, i):
            self.i = i

        def to_dict(self):
            return i

    trace = epsagon.trace.Trace()
    expected_dict = {
        'token': 'token',
        'app_name': 'app_name',
        'events': range(10),
        'exceptions': 'exceptions',
        'version': 'version',
        'platform': 'platform'
    }

    trace.token = expected_dict['token']
    trace.app_name = expected_dict['app_name']
    trace.events = [EventMock(i) for i in range(10)]
    trace.exceptions = expected_dict['exceptions']
    trace.version = expected_dict['version']
    trace.platform = expected_dict['platform']
    trace_dict = trace.to_dict()
    assert trace_dict == trace.to_dict()

def test_to_dict_empty():
    trace = epsagon.trace.Trace()
    assert trace.to_dict() == {
        'token': '',
        'app_name': '',
        'events': [],
        'exceptions': [],
        'version': epsagon.constants.__version__,
        'platform': 'Python {}.{}'.format(
            sys.version_info.major,
            sys.version_info.minor
        )

    }


@mock.patch('requests.post')
def test_send_traces_sanity(wrapped_post):
    tracer.token = 'a'
    tracer.send_traces()
    wrapped_post.assert_called_with(
        epsagon.constants.TRACE_COLLECTOR_URL,
        data=json.dumps(tracer.to_dict()),
        timeout=epsagon.constants.SEND_TIMEOUT
    )


@mock.patch('requests.post')
def test_send_traces_no_token(wrapped_post):
    tracer.send_traces()
    wrapped_post.assert_not_called()


@mock.patch('requests.post', side_effect=requests.ReadTimeout)
def test_send_traces_timeout(wrapped_post):
    tracer.token = 'a'
    tracer.send_traces()
    wrapped_post.assert_called_with(
        epsagon.constants.TRACE_COLLECTOR_URL,
        data=json.dumps(tracer.to_dict()),
        timeout=epsagon.constants.SEND_TIMEOUT
    )


@mock.patch('requests.post', side_effect=Exception)
def test_send_traces_post_error(wrapped_post):
    tracer.token = 'a'
    tracer.send_traces()
    wrapped_post.assert_called_with(
        epsagon.constants.TRACE_COLLECTOR_URL,
        data=json.dumps(tracer.to_dict()),
        timeout=epsagon.constants.SEND_TIMEOUT
    )


@mock.patch('epsagon.trace.Trace.initialize')
def test_init_sanity(wrapped_init):
    epsagon.trace.init('token', 'app-name')
    wrapped_init.assert_called_with(token='token', app_name='app-name')


@mock.patch('epsagon.trace.Trace.initialize')
def test_init_empty_app_name(wrapped_init):
    epsagon.trace.init('token', '')
    wrapped_init.assert_called_with(token='token', app_name='')
