"""
Common and builtin fixtures
"""
import pytest
from unittest.mock import MagicMock

import epsagon


class TestTransport(MagicMock):
    """

    """

    @property
    def last_trace(self):
        return self.send.call_args[0][0] if self.send.call_args else None

    @property
    def sent_traces(self):
        return [
            call_args[0][0] for call_args in self.send.call_args_list
        ]


@pytest.fixture(scope='function', autouse=True)
def trace_transport():
    epsagon.trace_factory.transport = TestTransport()
    epsagon.trace_factory.update_tracers()
    return epsagon.trace_factory.transport


@pytest.fixture(scope='module', autouse=True)
def init_epsagon():
    epsagon.init(token='test', app_name='test_app', metadata_only=False)
    return epsagon
