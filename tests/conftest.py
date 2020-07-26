"""
Common and builtin fixtures
"""
import pytest
from unittest.mock import MagicMock

import epsagon

TEST_TOKEN = 'test'
TEST_APP = 'test_app'
TEST_COLLECTOR = 'collector'


class TestTransport(MagicMock):
    """
    Mock trace transport for tests
    """

    @property
    def last_trace(self):
        """
        :return: The last Trace object that was sent (None if no trace was sent)
        """
        return self.send.call_args[0][0] if self.send.call_args else None

    @property
    def sent_traces(self):
        """
        :return: List of all the Trace objects that were sent
        """
        return [
            call_args[0][0] for call_args in self.send.call_args_list
        ]


@pytest.fixture(scope='function', autouse=False)
def trace_transport(clean_traces):
    """
    Fixture for overriding the trace transport class with a `TestTransport` instance
    :return: New `TestTransport` object
    """
    epsagon.trace_factory.transport = TestTransport()
    return epsagon.trace_factory.transport


def init_epsagon(**kwargs):
    """
    Call `epsagon.init` with default test args
    :param kwargs: Optional args to pass
    """
    default_kwargs = {
        'token': TEST_TOKEN,
        'app_name': TEST_APP,
        'metadata_only': False,
        'collector_url': TEST_COLLECTOR,
    }
    default_kwargs.update(kwargs)

    epsagon.init(**default_kwargs)


@pytest.fixture(scope='module', autouse=True)
def call_init_epsagon():
    """
    Init epsagon with default test values
    """
    init_epsagon()
    return epsagon


@pytest.fixture(scope='function', autouse=True)
def clean_traces():
    """
    Remove current traces from previous test (so that they will not effect the current test)
    """
    epsagon.trace_factory.singleton_trace = None
    epsagon.trace_factory.traces = {}
