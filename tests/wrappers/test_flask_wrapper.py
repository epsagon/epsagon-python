import mock
import pytest
import epsagon.wrappers.flask
import epsagon.constants
from flask import Flask


app = Flask('test')

@mock.patch(
    'epsagon.trace.tracer',
    prepare=mock.MagicMock(),
    send_traces=mock.MagicMock(),
    events=[],
    add_events=mock.MagicMock(),
    add_exception=mock.MagicMock()
)
def test_function_wrapper_sanity(trace_mock):
    runner_mock = mock.MagicMock(set_exception=mock.MagicMock())
    with mock.patch(
            'epsagon.runners.flask.FlaskRunner',
            side_effect=[runner_mock]
    ):
        epsagon.wrappers.flask.FlaskWrapper(app)
        app.before_request_funcs[None][0]()
        app.after_request_funcs[None][0](mock.MagicMock())
        app.teardown_request_funcs[None][0](None)

    runner_mock.set_exception.assert_not_called()
    trace_mock.prepare.assert_called()
    trace_mock.add_event.assert_called()
    trace_mock.send_traces.assert_called()
