"""
Test epsagon init
"""
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
    'EPSAGON_OBFUSCATE_SQL': 'FALSE',
    'EPSAGON_LOGGING_TRACING_ENABLED': 'TRUE',
    'AWS_LAMBDA_FUNCTION_NAME': None,
    'EPSAGON_STEPS_OUTPUT_PATH': '',
    'EPSAGON_SAMPLE_RATE': 0.5
}[x]))
def test_epsagon_wrapper_env_init(_wrapped_get, wrapped_init, wrapped_create):
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
        obfuscate_sql=False,
        logging_tracing_enabled=True,
        step_dict_output_path=None,
        sample_rate=0.5,
    )
    wrapped_create.assert_called_with("epsagon", "1234")


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
    'EPSAGON_STEPS_OUTPUT_PATH': '',
    'EPSAGON_ENDPOINTS_TO_IGNORE': '/health,/test',
    'EPSAGON_LOG_TRANSPORT': 'FALSE',
    'EPSAGON_SPLIT_ON_SEND': 'FALSE',
    'EPSAGON_PROPAGATE_LAMBDA_ID': 'FALSE',
    'EPSAGON_OBFUSCATE_SQL': 'FALSE',
    'EPSAGON_LOGGING_TRACING_ENABLED': 'TRUE',
    'AWS_LAMBDA_FUNCTION_NAME': None,
    'EPSAGON_SAMPLE_RATE': 0.5
}[x]))
def test_epsagon_wrapper_env_endpoints(_wrapped_get, wrapped_http):
    reload(epsagon)
    epsagon.init()
    wrapped_http.assert_called_with(['/health', '/test'])
