"""
Common tests helpers
"""
import mock


def get_tracer_patch_kwargs():
    return {
        'metadata_only': False,
        'disable_timeout_send': False,
        'prepare': mock.MagicMock(),
        'send_traces': mock.MagicMock(),
        'events': [],
        'add_event': mock.MagicMock(),
        'add_exception': mock.MagicMock()
    }