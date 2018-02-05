import os
import mock
import collections

os.environ['DISABLE_EPSAGON_PATCH'] = 'TRUE'
import epsagon.patcher

@mock.patch('__builtin__.__import__', side_effect=[True])
@mock.patch('epsagon.modules')
def test_patch_all(patched_modules, _):
    module_mock = mock.NonCallableMagicMock(patch=mock.MagicMock())
    patched_modules.MODULES = {'test': module_mock}
    epsagon.patcher.patch_all()
    module_mock.patch.assert_called()

@mock.patch('__builtin__.__import__', side_effect=ImportError())
@mock.patch('epsagon.modules')
def test_patch_all_import_error(patched_modules, _):
    module_mock = mock.NonCallableMagicMock(patch=mock.MagicMock())
    patched_modules.MODULES = {'test': module_mock}
    epsagon.patcher.patch_all()
    module_mock.patch.assert_not_called()


@mock.patch('__builtin__.__import__')
@mock.patch('epsagon.modules')
def test_patch_all_import_ok_then_error(patched_modules, patched_import):
    def import_side_effect():
        yield 'True'
        raise ImportError()

    patched_import.side_effect = import_side_effect()
    module1_mock = mock.NonCallableMagicMock(patch=mock.MagicMock())
    module2_mock = mock.NonCallableMagicMock(patch=mock.MagicMock())
    patched_modules.MODULES = collections.OrderedDict(
        [('module1', module1_mock, ), ('module2', module2_mock,)]
    )

    epsagon.patcher.patch_all()
    module1_mock.patch.assert_called()
    module2_mock.patch.assert_not_called()

