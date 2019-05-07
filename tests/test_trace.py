import sys
import mock
import json
import time
from datetime import datetime
import requests
import warnings
import epsagon.trace
import epsagon.constants
from epsagon.constants import (
    TRACE_COLLECTOR_URL,
    DEFAULT_REGION
)
from epsagon.trace import factory, MAX_EVENTS_PER_TYPE, TraceEncoder
from epsagon.utils import get_tc_url
from epsagon.common import ErrorCode

class ContextMock:
    def __init__(self, timeout):
        self.timeout = timeout

    def get_remaining_time_in_millis(self):
        return self.timeout

class EventMock(object):
    ORIGIN = 'mock'
    RESOURCE_TYPE = 'mock'

    def __init__(self):
        self.terminated = False
        self.exception = {}
        self.resource = {
            'metadata': {}
        }

    def terminate(self):
        self.terminated = True

    def identifier(self):
        return '{}{}'.format(self.ORIGIN, self.RESOURCE_TYPE)

    def to_dict(self):
        result = {
            'resource': self.resource
        }
        if self.exception:
            result['exception'] = self.exception
        return result


class RunnerEventMock(EventMock):
    def __init__(self):
        super(RunnerEventMock, self).__init__()
        self.terminated = True
        self.origin = 'runner'

    def terminate(self):
        pass

    def set_timeout(self):
        pass

    def set_exception(self, exception, traceback_data):
        self.error_code = ErrorCode.EXCEPTION
        self.exception['type'] = type(exception).__name__
        self.exception['message'] = str(exception)
        self.exception['traceback'] = traceback_data
        self.exception['time'] = time.time()


class EventMockWithCounter(EventMock):
    def __init__(self, i):
        super(EventMockWithCounter, self).__init__()
        self.i = i

    def to_dict(self):
        return {
            'i', self.i
        }


def setup_function(func):
    factory.get_trace().__init__()


def test_add_exception():
    stack_trace_format = 'stack trace %d'
    message_format = 'message %d'
    tested_exception_types = [
        ZeroDivisionError,
        RuntimeError,
        NameError,
        TypeError
    ]

    trace = factory.get_trace()
    for i, exception_type in enumerate(tested_exception_types):
        try:
            raise exception_type(message_format % i)
        except exception_type as e:
            trace.add_exception(e, stack_trace_format % i)

    assert len(trace.exceptions) == len(tested_exception_types)
    for i, exception_type in enumerate(tested_exception_types):
        current_exception = trace.exceptions[i]
        assert current_exception['type'] == str(exception_type)
        assert current_exception['message'] == message_format % i
        assert current_exception['traceback'] == stack_trace_format % i
        assert type(current_exception['time']) == float


def test_add_exception_with_additional_data():
    stack_trace_format = 'stack trace %d'
    message_format = 'message %d'
    tested_exception_types = [
        ZeroDivisionError,
        RuntimeError,
        NameError,
        TypeError
    ]

    additional_data = {'key': 'value', 'key2': 'othervalue'}
    trace = factory.get_trace()

    for i, exception_type in enumerate(tested_exception_types):
        try:
            raise exception_type(message_format % i)
        except exception_type as e:
            trace.add_exception(e, stack_trace_format % i, additional_data)

    assert len(trace.exceptions) == len(tested_exception_types)
    for i, exception_type in enumerate(tested_exception_types):
        current_exception = trace.exceptions[i]
        assert current_exception['type'] == str(exception_type)
        assert current_exception['message'] == message_format % i
        assert current_exception['traceback'] == stack_trace_format % i
        assert type(current_exception['time']) == float
        assert current_exception['additional_data'] == additional_data


def test_prepare():
    trace = factory.get_trace()
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always')
        trace.prepare()
        assert not list(trace.events())
        assert trace.exceptions == []
        assert len(w) == 1
    trace.clear_events()
    trace.add_event(EventMock())
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always')
        trace.prepare()
        assert not list(trace.events())
        assert trace.exceptions == []
        assert len(w) == 1

    trace.clear_events()
    trace.add_event(EventMock())
    with warnings.catch_warnings(record=True) as w:
        trace.prepare()
        trace.prepare()  # this call should NOT trigger a warning
        assert not list(trace.events())
        assert trace.exceptions == []
        assert len(w) == 1


def test_initialize():
    app_name = 'app-name'
    token = 'token'
    collector_url = 'collector_url'
    metadata_only = False
    disable_on_timeout = False
    debug = True
    trace = factory.get_trace()
    trace.initialize(
        app_name, token, collector_url, metadata_only, disable_on_timeout, debug
    )
    assert trace.app_name == app_name
    assert trace.token == token
    assert trace.collector_url == collector_url
    assert trace.disable_timeout_send == disable_on_timeout
    assert trace.debug == debug

    trace.initialize(app_name, '', '', False, False, False)
    assert trace.app_name == app_name
    assert trace.token == ''
    assert trace.collector_url == ''
    assert trace.metadata_only == False
    assert trace.disable_timeout_send == False
    assert trace.debug == False

    trace.initialize('', '', '', True, True, False)
    assert trace.app_name == ''
    assert trace.token == ''
    assert trace.collector_url == ''
    assert trace.metadata_only == True
    assert trace.disable_timeout_send == True
    assert trace.debug == False


def test_load_from_dict():
    for i in range(2):  # validate a new trace is created each time
        number_of_events = 10
        trace_data = {
            'app_name': 'app_name',
            'token': 'token',
            'version': 'version',
            'platform': 'platform',
            'events': [EventMockWithCounter(i) for i in range(number_of_events)]
        }

        with mock.patch('epsagon.event.BaseEvent.load_from_dict',
                        side_effect=(lambda x: x)):
            new_trace = epsagon.trace.Trace.load_from_dict(trace_data)
            assert new_trace.app_name == trace_data['app_name']
            assert new_trace.token == trace_data['token']
            assert new_trace.version == trace_data['version']
            assert new_trace.platform == trace_data['platform']
            assert list(new_trace.events()) == trace_data['events']
            assert new_trace.exceptions == []


def test_load_from_dict_with_exceptions():
    for i in range(2):  # validate a new trace is created each time
        number_of_events = 10
        trace_data = {
            'app_name': 'app_name',
            'token': 'token',
            'version': 'version',
            'platform': 'platform',
            'events': [EventMockWithCounter(i)
                       for i in range(number_of_events)],
            'exceptions': 'test_exceptions'
        }

        with mock.patch('epsagon.event.BaseEvent.load_from_dict',
                        side_effect=(lambda x: x)):
            new_trace = epsagon.trace.Trace.load_from_dict(trace_data)
            assert new_trace.app_name == trace_data['app_name']
            assert new_trace.token == trace_data['token']
            assert new_trace.version == trace_data['version']
            assert new_trace.platform == trace_data['platform']
            assert list(new_trace.events()) == trace_data['events']
            assert new_trace.exceptions == trace_data['exceptions']


def test_add_event():
    event = EventMock()
    trace = factory.get_trace()
    trace.clear_events()
    for i in range(10):  # verify we can add more then 1 event
        trace.add_event(event)

        assert event is list(trace.events())[i]
        assert event.terminated


def test_add_too_many_events():
    event = EventMock()
    trace = factory.get_trace()
    trace.clear_events()
    for _ in range(MAX_EVENTS_PER_TYPE * 2):  # verify we can add more then 1 event
        trace.add_event(event)

    assert len(trace.to_dict()['events']) == MAX_EVENTS_PER_TYPE


def test_to_dict():
    trace = epsagon.trace.Trace()
    expected_dict = {
        'token': 'token',
        'app_name': 'app_name',
        'events': [EventMockWithCounter(i)
                   for i in range(10)],
        'exceptions': 'exceptions',
        'version': 'version',
        'platform': 'platform'
    }

    trace.token = expected_dict['token']
    trace.app_name = expected_dict['app_name']
    for event in [EventMockWithCounter(i) for i in range(10)]:
        trace.add_event(event)
    trace.exceptions = expected_dict['exceptions']
    trace.version = expected_dict['version']
    trace.platform = expected_dict['platform']
    trace_dict = trace.to_dict()
    assert trace_dict == trace.to_dict()


def test_custom_labels_sanity():
    event = RunnerEventMock()
    trace = factory.get_trace()
    trace.clear_events()
    trace.set_runner(event)
    trace.add_label('test_label', 'test_value')
    trace.add_label('test_label_2', 42)
    trace.add_label('test_label_3', 42.2)
    trace.add_label('test_label_invalid', {})
    trace_metadata = trace.to_dict()['events'][0]['resource']['metadata']

    assert trace_metadata.get('labels') is not None
    assert json.loads(trace_metadata['labels']) == {
        'test_label': 'test_value',
        'test_label_2': '42',
        'test_label_3': '42.2',
    }


def test_set_error_sanity():
    event = RunnerEventMock()
    trace = factory.get_trace()
    trace.clear_events()
    trace.set_runner(event)
    msg = 'oops'
    trace.set_error(ValueError(msg), 'test_value')

    assert trace.to_dict()['events'][0]['exception']['message'] == msg

def test_custom_labels_override_trace():
    event = RunnerEventMock()
    trace = factory.get_trace()
    trace.clear_events()
    trace.set_runner(event)
    trace.add_label('test_label', 'test_value1')
    trace.add_label('test_label', 'test_value2')
    trace_metadata = trace.to_dict()['events'][0]['resource']['metadata']

    assert trace_metadata.get('labels') is not None
    assert json.loads(trace_metadata['labels']) == {'test_label': 'test_value2'}


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


def test_set_timeout_handler_emtpy_context():
    # Has no 'get_remaining_time_in_millis' attribute
    factory.get_trace().set_timeout_handler({})


@mock.patch('requests.Session.post')
def test_timeout_handler_called(wrapped_post):
    """
    Sanity
    """
    context = ContextMock(300)
    runner = RunnerEventMock()
    trace = factory.get_trace()
    trace.token = 'a'
    trace.set_timeout_handler(context)
    trace.set_runner(runner)
    time.sleep(0.5)

    assert trace.trace_sent
    assert wrapped_post.called


@mock.patch('requests.Session.post')
def test_timeout_send_not_called_twice(wrapped_post):
    """
    In case of a timeout send trace, validate no trace
    is sent afterwards (if the flow continues)
    """
    context = ContextMock(300)
    runner = RunnerEventMock()
    trace = factory.get_trace()
    trace.token = 'a'
    trace.set_timeout_handler(context)
    trace.set_runner(runner)
    time.sleep(0.5)

    assert trace.trace_sent
    assert wrapped_post.call_count == 1


@mock.patch('requests.Session.post')
def test_timeout_happyflow_handler_call(wrapped_post):
    """
    Test in case we already sent the traces on happy flow,
    that timeout handler call won't send them again.
    """
    context = ContextMock(300)
    runner = RunnerEventMock()
    trace = factory.get_trace()
    trace.set_runner(runner)

    trace.token = 'a'
    trace.send_traces()

    trace.set_timeout_handler(context)
    time.sleep(0.5)

    assert trace.trace_sent
    assert wrapped_post.call_count == 1


@mock.patch('requests.Session.post')
def test_send_traces_sanity(wrapped_post):
    trace = factory.get_trace()
    trace.token = 'a'
    trace.send_traces()
    wrapped_post.assert_called_with(
        '',
        data=json.dumps(tracer.to_dict()),
        timeout=epsagon.constants.SEND_TIMEOUT,
        headers={'Authorization': 'Bearer {}'.format(tracer.token)}
    )


@mock.patch('requests.Session.post')
def test_send_traces_no_token(wrapped_post):
    trace = factory.get_trace()
    trace.send_traces()
    wrapped_post.assert_not_called()


@mock.patch('requests.Session.post', side_effect=requests.ReadTimeout)
def test_send_traces_timeout(wrapped_post):
    trace = factory.get_trace()

    trace.token = 'a'
    trace.send_traces()
    wrapped_post.assert_called_with(
        '',
        data=json.dumps(tracer.to_dict()),
        timeout=epsagon.constants.SEND_TIMEOUT,
        headers={'Authorization': 'Bearer {}'.format(tracer.token)}
    )


@mock.patch('requests.Session.post', side_effect=Exception)
def test_send_traces_post_error(wrapped_post):
    trace = factory.get_trace()

    trace.token = 'a'
    trace.send_traces()
    wrapped_post.assert_called_with(
        '',
        data=json.dumps(tracer.to_dict()),
        timeout=epsagon.constants.SEND_TIMEOUT,
        headers={'Authorization': 'Bearer {}'.format(tracer.token)}
    )


@mock.patch('epsagon.trace.TraceFactory.initialize')
def test_init_sanity(wrapped_init):
    epsagon.utils.init(
        token='token',
        app_name='app-name',
        collector_url='collector',
        metadata_only=False
    )
    wrapped_init.assert_called_with(
        token='token',
        app_name='app-name',
        collector_url='collector',
        metadata_only=False,
        disable_timeout_send=False,
        debug=False
    )


@mock.patch('epsagon.trace.TraceFactory.initialize')
def test_init_empty_app_name(wrapped_init):
    epsagon.utils.init(
        token='token',
        app_name='',
        collector_url='collector',
        metadata_only=False,
        use_ssl=True,
    )
    wrapped_init.assert_called_with(
        token='token',
        app_name='',
        collector_url='collector',
        metadata_only=False,
        disable_timeout_send=False,
        debug=False
    )


@mock.patch('epsagon.trace.TraceFactory.initialize')
def test_init_empty_collector_url(wrapped_init):
    epsagon.utils.init(token='token', app_name='app-name', metadata_only=False)
    wrapped_init.assert_called_with(
        token='token',
        app_name='app-name',
        collector_url=get_tc_url(True),
        metadata_only=False,
        disable_timeout_send=False,
        debug=False
    )


@mock.patch('epsagon.trace.TraceFactory.initialize')
def test_init_no_ssl_no_url(wrapped_init):
    epsagon.utils.init(token='token', app_name='app-name', metadata_only=False,
                       use_ssl=False)
    wrapped_init.assert_called_with(
        token='token',
        app_name='app-name',
        metadata_only=False,
        collector_url=TRACE_COLLECTOR_URL.format(
            region=DEFAULT_REGION,
            protocol="http://"
        ),
        disable_timeout_send=False,
        debug=False
    )


@mock.patch('epsagon.trace.TraceFactory.initialize')
def test_init_ssl_no_url(wrapped_init):
    epsagon.utils.init(
        token='token',
        app_name='app-name',
        metadata_only=False,
        use_ssl=True
    )
    wrapped_init.assert_called_with(
        token='token',
        app_name='app-name',
        metadata_only=False,
        collector_url=TRACE_COLLECTOR_URL.format(
            region=DEFAULT_REGION,
            protocol="https://"
        ),
        disable_timeout_send=False,
        debug=False
    )


@mock.patch('epsagon.trace.TraceFactory.initialize')
def test_init_ssl_with_url(wrapped_init):
    epsagon.utils.init(
        token='token',
        app_name='app-name',
        collector_url="http://abc.com",
        metadata_only=False,
        use_ssl=True
    )
    wrapped_init.assert_called_with(
        token='token',
        app_name='app-name',
        metadata_only=False,
        collector_url="http://abc.com",
        disable_timeout_send=False,
        debug=False
    )


@mock.patch('epsagon.trace.TraceFactory.initialize')
def test_init_no_ssl_with_url(wrapped_init):
    epsagon.utils.init(
        token='token',
        app_name='app-name',
        collector_url="http://abc.com",
        metadata_only=False,
        use_ssl=False
    )
    wrapped_init.assert_called_with(
        token='token',
        app_name='app-name',
        metadata_only=False,
        collector_url="http://abc.com",
        disable_timeout_send=False,
        debug=False
    )


@mock.patch('requests.Session.post', side_effect=requests.ReadTimeout)
def test_event_with_datetime(wrapped_post):
    tracer.token = 'a'
    event = EventMock()
    event.resource['metadata'] = datetime.fromtimestamp(1000)
    tracer.add_event(event)
    tracer.send_traces()
    wrapped_post.assert_called_with(
        '',
        data=json.dumps(tracer.to_dict(), cls=TraceEncoder),
        timeout=epsagon.constants.SEND_TIMEOUT,
        headers={'Authorization': 'Bearer {}'.format(tracer.token)}
    )
