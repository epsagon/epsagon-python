import mock
import epsagon
import os
from imp import reload


@mock.patch('epsagon.patcher.patch_all')
@mock.patch('os.environ.get', side_effect=['FALSE', 'FALSE'])
def test_epsagon(wrapped_get, wrapped_patch):
    reload(epsagon)
    wrapped_get.assert_has_calls([
        mock.call('DISABLE_EPSAGON'),
        mock.call('DISABLE_EPSAGON_PATCH'),
    ])
    wrapped_patch.assert_called()


@mock.patch('epsagon.patcher.patch_all')
@mock.patch('os.environ.get', side_effect=['FALSE', 'TRUE'])
def test_epsagon_no_patch_env(wrapped_get, wrapped_patch):
    reload(epsagon)
    wrapped_get.assert_has_calls([
        mock.call('DISABLE_EPSAGON'),
        mock.call('DISABLE_EPSAGON_PATCH'),
    ])
    wrapped_patch.assert_not_called()


@mock.patch('epsagon.patcher.patch_all')
@mock.patch('os.environ.get', side_effect=['TRUE', 'TRUE'])
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

