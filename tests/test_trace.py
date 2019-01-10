import sys
import mock
import json
import requests
import warnings
import epsagon.trace
import epsagon.constants
from epsagon.constants import (
    TRACE_COLLECTOR_URL,
    DEFAULT_REGION
)
from epsagon.trace import tracer, MAX_EVENTS_PER_TYPE
from epsagon.utils import get_tc_url
from epsagon.common import ErrorCode


class EventMock(object):
    ORIGIN = 'mock'
    RESOURCE_TYPE = 'mock'

    def terminate(self):
        self.terminated = True


class RunnerEventMock(EventMock):
    def __init__(self, i):
        super(EventMockWithCounter, self).__init__()
        self.origin = 'runner'
        self.terminated = True
        self.resource = {
            'metadata': {}
        }

    def to_dict(self):
        return {
            'resource': self.resource
        }

    def terminate(self):
        pass


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
            tracer.add_exception(e, stack_trace_format % i)

    assert len(tracer.exceptions) == len(tested_exception_types)
    for i, exception_type in enumerate(tested_exception_types):
        current_exception = tracer.exceptions[i]
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
    for i, exception_type in enumerate(tested_exception_types):
        try:
            raise exception_type(message_format % i)
        except exception_type as e:
            tracer.add_exception(e, stack_trace_format % i, additional_data)

    assert len(tracer.exceptions) == len(tested_exception_types)
    for i, exception_type in enumerate(tested_exception_types):
        current_exception = tracer.exceptions[i]
        assert current_exception['type'] == str(exception_type)
        assert current_exception['message'] == message_format % i
        assert current_exception['traceback'] == stack_trace_format % i
        assert type(current_exception['time']) == float
        assert current_exception['additional_data'] == additional_data


def test_prepare():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always')
        tracer.prepare()
        assert not list(tracer.events())
        assert tracer.exceptions == []
        assert len(w) == 1

    tracer.add_event(EventMock())
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always')
        tracer.prepare()
        assert not list(tracer.events())
        assert tracer.exceptions == []
        assert len(w) == 1

    tracer.add_event(EventMock())
    with warnings.catch_warnings(record=True) as w:
        tracer.prepare()
        tracer.prepare()  # this call should NOT trigger a warning
        assert not list(tracer.events())
        assert tracer.exceptions == []
        assert len(w) == 1


def test_initialize():
    app_name = 'app-name'
    token = 'token'
    collector_url = 'collector_url'
    metadata_only = False
    debug = True
    tracer.initialize(
        app_name, token, collector_url, metadata_only, debug
    )
    assert tracer.app_name == app_name
    assert tracer.token == token
    assert tracer.collector_url == collector_url
    assert tracer.debug == debug

    tracer.initialize(app_name, '', '', False, False)
    assert tracer.app_name == app_name
    assert tracer.token == ''
    assert tracer.collector_url == ''
    assert tracer.metadata_only == False
    assert tracer.debug == False

    tracer.initialize('', '', '', True, False)
    assert tracer.app_name == ''
    assert tracer.token == ''
    assert tracer.collector_url == ''
    assert tracer.metadata_only == True
    assert tracer.debug == False


def test_load_from_dict():
    for i in range(2):  # validate a new trace is created each time
        number_of_events = 10
        trace_data = {
            'app_name': 'app_name',
            'token': 'token',
            'version': 'version',
            'platform': 'platform',
            'events': [i for i in range(number_of_events)]
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
            'events': [i for i in range(number_of_events)],
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
    for i in range(10):  # verify we can add more then 1 event
        tracer.add_event(event)
        assert event is len(tracer.events())[i]
        assert event.terminated


def test_add_too_many_events():
    event = EventMock()
    for _ in range(MAX_EVENTS_PER_TYPE * 2):  # verify we can add more then 1 event
        tracer.add_event(event)

    assert len(trace.to_dict()['events']) == MAX_EVENTS_PER_TYPE


def test_to_dict():
    class EventMockWithCounter(EventMock):
        def __init__(self, i):
            super(EventMockWithCounter, self).__init__()
            self.i = i

        def to_dict(self):
            return self.i

    trace = epsagon.trace.Trace()
    expected_dict = {
        'token': 'token',
        'app_name': 'app_name',
        'events': [i for i in range(10)],
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
    tracer.add_event(event)
    tracer.add_label('test_label', 'test_value')
    trace_metadata = tracer.to_dict()['events'][0]['resource']['metadata']

    assert trace_metadata.get('labels') is not None
    assert json.loads(trace_metadata['labels']) == {'test_label': 'test_value'}


def test_custom_labels_override_trace():
    event = RunnerEventMock()
    tracer.add_event(event)
    tracer.add_label('test_label', 'test_value1')
    tracer.add_label('test_label', 'test_value2')
    trace_metadata = tracer.to_dict()['events'][0]['resource']['metadata']

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


@mock.patch('requests.post')
def test_send_traces_sanity(wrapped_post):
    tracer.token = 'a'
    tracer.send_traces()
    wrapped_post.assert_called_with(
        '',
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
        '',
        data=json.dumps(tracer.to_dict()),
        timeout=epsagon.constants.SEND_TIMEOUT
    )


@mock.patch('requests.post', side_effect=Exception)
def test_send_traces_post_error(wrapped_post):
    tracer.token = 'a'
    tracer.send_traces()
    wrapped_post.assert_called_with(
        '',
        data=json.dumps(tracer.to_dict()),
        timeout=epsagon.constants.SEND_TIMEOUT
    )


@mock.patch('epsagon.trace.Trace.initialize')
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
        debug=False
    )


@mock.patch('epsagon.trace.Trace.initialize')
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
        debug=False
    )


@mock.patch('epsagon.trace.Trace.initialize')
def test_init_empty_collector_url(wrapped_init):
    epsagon.utils.init(token='token', app_name='app-name', metadata_only=False)
    wrapped_init.assert_called_with(
        token='token',
        app_name='app-name',
        collector_url=get_tc_url(True),
        metadata_only=False,
        debug=False
    )


@mock.patch('epsagon.trace.Trace.initialize')
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
        debug=False
    )


@mock.patch('epsagon.trace.Trace.initialize')
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
        debug=False
    )


@mock.patch('epsagon.trace.Trace.initialize')
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
        debug=False
    )


@mock.patch('epsagon.trace.Trace.initialize')
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
        debug=False
    )
