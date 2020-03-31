import mock
import epsagon
import os
from imp import reload
from epsagon.trace_transports import HTTPTransport


@mock.patch('epsagon.patcher.patch_all')
@mock.patch('os.getenv', side_effect=(lambda x: {
    'EPSAGON_HANDLER': None,
    'DISABLE_EPSAGON': 'FALSE',
    'DISABLE_EPSAGON_PATCH': 'FALSE',
}[x]))
def test_epsagon(wrapped_get, wrapped_patch):
    reload(epsagon)
    wrapped_get.assert_has_calls([
        mock.call('DISABLE_EPSAGON'),
        mock.call('DISABLE_EPSAGON_PATCH'),
    ])
    wrapped_patch.assert_called()


@mock.patch('epsagon.patcher.patch_all')
@mock.patch('os.getenv', side_effect=(lambda x: {
    'EPSAGON_HANDLER': None,
    'DISABLE_EPSAGON': 'FALSE',
    'DISABLE_EPSAGON_PATCH': 'TRUE',
}[x]))
def test_epsagon_no_patch_env(wrapped_get, wrapped_patch):
    reload(epsagon)
    wrapped_get.assert_has_calls([
        mock.call('DISABLE_EPSAGON'),
        mock.call('DISABLE_EPSAGON_PATCH'),
    ])
    wrapped_patch.assert_not_called()


@mock.patch('epsagon.patcher.patch_all')
@mock.patch('os.getenv', side_effect=(lambda x: {
    'EPSAGON_HANDLER': None,
    'DISABLE_EPSAGON': 'TRUE',
    'DISABLE_EPSAGON_PATCH': 'TRUE',
}[x]))
def test_epsagon_disable_epsagon_and_disable_patch(wrapped_get, wrapped_patch):
    reload(epsagon)
    wrapped_get.assert_has_calls([
        mock.call('DISABLE_EPSAGON'),
        mock.call('DISABLE_EPSAGON_PATCH'),
    ])
    wrapped_patch.assert_not_called()
    assert os.environ['DISABLE_EPSAGON_PATCH'] == 'TRUE'

    def dummy():
        return True
    assert epsagon.lambda_wrapper(dummy) is dummy
    assert epsagon.step_lambda_wrapper(dummy) is dummy
    assert epsagon.azure_wrapper(dummy) is dummy
    assert epsagon.python_wrapper(dummy) is dummy
    assert epsagon.gcp_wrapper(dummy) is dummy


@mock.patch('os.getenv', side_effect=(lambda x: {
    'EPSAGON_HANDLER': 'epsagon.lambda_wrapper',
    'DISABLE_EPSAGON': 'FALSE',
    'DISABLE_EPSAGON_PATCH': 'FALSE',
    'EPSAGON_SSL': 'FALSE',
    'EPSAGON_TOKEN': 'FALSE',
    'EPSAGON_APP_NAME': 'FALSE',
    'EPSAGON_COLLECTOR_URL': 'FALSE',
    'EPSAGON_METADATA': 'FALSE',
    'EPSAGON_DISABLE_ON_TIMEOUT': 'FALSE',
    'EPSAGON_DEBUG': 'FALSE',
    'EPSAGON_SEND_TRACE_ON_ERROR': 'FALSE',
    'EPSAGON_URLS_TO_IGNORE': '',
    'EPSAGON_ENDPOINTS_TO_IGNORE': '',
    'EPSAGON_IGNORED_KEYS': '',
    'EPSAGON_ALLOWED_KEYS': '',
}[x]))
def test_epsagon_wrapper_env_init(wrapped_get):
    reload(epsagon)
    epsagon.init()
    wrapped_get.assert_has_calls([
        mock.call('EPSAGON_HANDLER'),
        mock.call('EPSAGON_SSL'),
        mock.call('EPSAGON_URLS_TO_IGNORE'),
        mock.call('EPSAGON_ENDPOINTS_TO_IGNORE'),
        mock.call('EPSAGON_IGNORED_KEYS'),
        mock.call('EPSAGON_ALLOWED_KEYS'),
        mock.call('EPSAGON_TOKEN'),
        mock.call('EPSAGON_APP_NAME'),
        mock.call('EPSAGON_COLLECTOR_URL'),
        mock.call('EPSAGON_METADATA'),
        mock.call('EPSAGON_DISABLE_ON_TIMEOUT'),
        mock.call('EPSAGON_DEBUG'),
        mock.call('EPSAGON_SEND_TRACE_ON_ERROR'),
        mock.call('EPSAGON_HANDLER'),
        mock.call('DISABLE_EPSAGON'),
        mock.call('DISABLE_EPSAGON_PATCH'),
        mock.call('EPSAGON_SSL'),
        mock.call('EPSAGON_URLS_TO_IGNORE'),
        mock.call('EPSAGON_ENDPOINTS_TO_IGNORE'),
        mock.call('EPSAGON_IGNORED_KEYS'),
        mock.call('EPSAGON_ALLOWED_KEYS'),
        mock.call('EPSAGON_TOKEN'),
        mock.call('EPSAGON_APP_NAME'),
        mock.call('EPSAGON_COLLECTOR_URL'),
        mock.call('EPSAGON_METADATA'),
        mock.call('EPSAGON_DISABLE_ON_TIMEOUT'),
        mock.call('EPSAGON_DEBUG'),
        mock.call('EPSAGON_SEND_TRACE_ON_ERROR'),
        mock.call('EPSAGON_PROPAGATE_LAMBDA_ID')
    ])


default_http = HTTPTransport("epsagon", "1234")


@mock.patch('epsagon.utils.create_transport', side_effect=lambda x, y: default_http)
@mock.patch('epsagon.trace.TraceFactory.initialize')
@mock.patch('os.getenv', side_effect=(lambda x: {
    'EPSAGON_HANDLER': 'epsagon.lambda_wrapper',
    'DISABLE_EPSAGON': 'FALSE',
    'DISABLE_EPSAGON_PATCH': 'FALSE',
    'EPSAGON_SSL': 'FALSE',
    'EPSAGON_TOKEN': '1234',
    'EPSAGON_APP_NAME': 'test',
    'EPSAGON_COLLECTOR_URL': 'epsagon',
    'EPSAGON_METADATA': 'TRUE',
    'EPSAGON_DISABLE_ON_TIMEOUT': 'FALSE',
    'EPSAGON_DEBUG': 'FALSE',
    'EPSAGON_SEND_TRACE_ON_ERROR': 'FALSE',
    'EPSAGON_URLS_TO_IGNORE': '',
    'EPSAGON_IGNORED_KEYS': '',
    'EPSAGON_ALLOWED_KEYS': '',
    'EPSAGON_LOG_TRANSPORT': 'FALSE',
    'EPSAGON_ENDPOINTS_TO_IGNORE': '',
    'EPSAGON_SPLIT_ON_SEND': 'FALSE',
    'EPSAGON_PROPAGATE_LAMBDA_ID': 'FALSE',
}[x]))
def test_epsagon_wrapper_env_init(_wrapped_get, wrapped_init, _create):
    reload(epsagon)
    epsagon.init()
    wrapped_init.assert_called_with(
        app_name='test',
        token='1234',
        collector_url='epsagon',
        metadata_only=True,
        disable_timeout_send=False,
        debug=False,
        send_trace_only_on_error=False,
        url_patterns_to_ignore=None,
        keys_to_ignore=None,
        keys_to_allow=None,
        transport=default_http,
        split_on_send=False,
        propagate_lambda_id=False,
    )


@mock.patch('epsagon.http_filters.add_ignored_endpoints')
@mock.patch('os.getenv', side_effect=(lambda x: {
    'EPSAGON_HANDLER': 'epsagon.lambda_wrapper',
    'DISABLE_EPSAGON': 'FALSE',
    'DISABLE_EPSAGON_PATCH': 'FALSE',
    'EPSAGON_SSL': 'FALSE',
    'EPSAGON_TOKEN': '1234',
    'EPSAGON_APP_NAME': 'test',
    'EPSAGON_COLLECTOR_URL': 'epsagon',
    'EPSAGON_METADATA': 'TRUE',
    'EPSAGON_DISABLE_ON_TIMEOUT': 'FALSE',
    'EPSAGON_DEBUG': 'FALSE',
    'EPSAGON_SEND_TRACE_ON_ERROR': 'FALSE',
    'EPSAGON_URLS_TO_IGNORE': '',
    'EPSAGON_IGNORED_KEYS': '',
    'EPSAGON_ALLOWED_KEYS': '',
    'EPSAGON_ENDPOINTS_TO_IGNORE': '/health,/test',
    'EPSAGON_LOG_TRANSPORT': 'FALSE',
    'EPSAGON_SPLIT_ON_SEND': 'FALSE',
    'EPSAGON_PROPAGATE_LAMBDA_ID': 'FALSE',
}[x]))
def test_epsagon_wrapper_env_endpoints(_wrapped_get, wrapped_http):
    reload(epsagon)
    epsagon.init()
    wrapped_http.assert_called_with(['/health', '/test'])
