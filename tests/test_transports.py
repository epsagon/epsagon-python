import time
import pytest
import urllib3
from epsagon.trace_transports import HTTPTransport
from epsagon.trace import (trace_factory)


def test_sanity(httpserver):
    collector_url = '/collector'
    httpserver.expect_request(collector_url).respond_with_data("success")
    http_transport = HTTPTransport(httpserver.url_for(collector_url), 'token')
    trace = trace_factory.get_or_create_trace()
    http_transport.send(trace)


def test_timeout():
    start_time = time.time()
    # non-routable IP address, will result in a timeout
    http_transport = HTTPTransport('http://10.255.255.1', 'token')
    trace = trace_factory.get_or_create_trace()

    # This will make sure we get TimeoutError and not MaxRetryError
    with pytest.raises(urllib3.exceptions.TimeoutError):
        http_transport.send(trace)

    duration = time.time() - start_time

    # Making sure that an unreachable url will result in duration almost equal to the
    # timeout duration set
    assert http_transport.timeout < duration < http_transport.timeout + 0.3
