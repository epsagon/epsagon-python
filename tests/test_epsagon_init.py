import mock
import epsagon
import os
from imp import reload

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


@mock.patch('epsagon.utils.init')
@mock.patch('os.getenv', side_effect=(lambda x: {
    'EPSAGON_HANDLER': 'epsagon.lambda_wrapper',
    'DISABLE_EPSAGON': 'FALSE',
    'DISABLE_EPSAGON_PATCH': 'FALSE',
    'EPSAGON_SSL': 'FALSE',
    'EPSAGON_TOKEN': 'FALSE',
    'EPSAGON_APP_NAME': 'FALSE',
    'EPSAGON_COLLECTOR_URL': 'FALSE',
    'EPSAGON_METADATA': 'FALSE',
    'EPSAGON_DEBUG': 'FALSE',
}[x]))
def test_epsagon_wrapper_env_init(wrapped_get, wrapped_init):
    reload(epsagon)
    wrapped_get.assert_has_calls([
        mock.call('DISABLE_EPSAGON'),
        mock.call('DISABLE_EPSAGON_PATCH'),
        mock.call('EPSAGON_HANDLER'),
        mock.call('EPSAGON_SSL'),
        mock.call('EPSAGON_TOKEN'),
        mock.call('EPSAGON_APP_NAME'),
        mock.call('EPSAGON_COLLECTOR_URL'),
        mock.call('EPSAGON_METADATA'),
        mock.call('EPSAGON_DEBUG'),
    ])
    wrapped_init.assert_called()


@mock.patch('epsagon.trace.Trace.initialize')
@mock.patch('os.getenv', side_effect=(lambda x: {
    'EPSAGON_HANDLER': 'epsagon.lambda_wrapper',
    'DISABLE_EPSAGON': 'FALSE',
    'DISABLE_EPSAGON_PATCH': 'FALSE',
    'EPSAGON_SSL': 'FALSE',
    'EPSAGON_TOKEN': '1234',
    'EPSAGON_APP_NAME': 'test',
    'EPSAGON_COLLECTOR_URL': 'epsagon',
    'EPSAGON_METADATA': 'TRUE',
    'EPSAGON_DEBUG': 'FALSE',
}[x]))
def test_epsagon_wrapper_env_init(_wrapped_get, wrapped_init):
    reload(epsagon)
    wrapped_init.assert_called_with(
        app_name='test',
        token='1234',
        collector_url='epsagon',
        metadata_only=True,
        debug=False
    )
