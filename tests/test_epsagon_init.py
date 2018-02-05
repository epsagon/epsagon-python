import mock
import epsagon

@mock.patch('epsagon.patcher.patch_all')
@mock.patch('os.environ.get', side_effect=['FALSE'])
def test_epsagon(wrapped_get, wrapped_patch):
    reload(epsagon)
    wrapped_patch.assert_called()

@mock.patch('epsagon.patcher.patch_all')
@mock.patch('os.environ.get', side_effect=['TRUE'])
def test_epsagon_no_patch_env(wrapped_get, wrapped_patch):
    reload(epsagon)
    wrapped_get.assert_called_with('DISABLE_EPSAGON_PATCH')
    wrapped_patch.assert_not_called()
