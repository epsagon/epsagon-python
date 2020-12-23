"""
Common tests helpers
"""
import mock
import requests
from threading import Thread


def get_tracer_patch_kwargs():
    return {
        'metadata_only': False,
        'disable_timeout_send': False,
        'prepare': mock.MagicMock(),
        'send_traces': mock.MagicMock(),
        'events': [],
        'add_event': mock.MagicMock(),
        'add_exception': mock.MagicMock(),
        'set_runner': mock.MagicMock()
    }


def _send_get_request(target_url, results):
    """
    Sends a get requests to a given target URL string
    :return: the given target url
    """
    requests.get(target_url)
    results.append(target_url)


def multiple_threads_handler(threads_count=3):
    """
    Invokes `threads_count` new threads, each performs an HTTP get request.
    Waits for all threads and validates a result has been returned from each
    thread.
    """
    threads = []
    results = []
    for i in range(threads_count):
        thread = Thread(target = _send_get_request, args = ("http://google.com", results))
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join()
    assert len(results) == threads_count
