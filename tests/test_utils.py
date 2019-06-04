import epsagon.trace
import epsagon.utils
import epsagon.wrappers.http_filters
from epsagon.trace import trace_factory


def setup_function(func):
    trace_factory.get_or_create_trace()


def test_blacklist_url():
    """
    Test is_blacklisted_url functionality.
    :return: None
    """

    epsagon.wrappers.http_filters.BLACKLIST_URLS = {
        str.endswith: [
            '.com',
        ],
        str.__contains__: [
            'restricted',
        ],
    }

    assert epsagon.wrappers.http_filters.is_blacklisted_url('http://www.google.com')
    assert epsagon.wrappers.http_filters.is_blacklisted_url('https://www.restricted-site.org')
    assert epsagon.wrappers.http_filters.is_blacklisted_url('http://www.restricted-site.com')
    assert not epsagon.wrappers.http_filters.is_blacklisted_url('https://www.com.org')
    assert not epsagon.wrappers.http_filters.is_blacklisted_url('http://www.google.org')


def test_original_blacklist_url():
    """
    Validate original needed URLs are in.
    :return: None
    """

    assert epsagon.wrappers.http_filters.is_blacklisted_url('http://tc.us-east-1.epsagon.com')
    assert epsagon.wrappers.http_filters.is_blacklisted_url('https://client.tc.epsagon.com')


def test_trace_blacklist():
    """
    Validate trace URL Blacklist mechanism.
    :return: None
    """
    trace_factory.get_trace().url_patterns_to_ignore = set(('test.net', 'test2.net'))
    assert epsagon.wrappers.http_filters.is_payload_collection_blacklisted('http://www.test.net')
    assert epsagon.wrappers.http_filters.is_payload_collection_blacklisted('http://www.bla.test.net')
    assert not epsagon.wrappers.http_filters.is_payload_collection_blacklisted('http://www.test.new.net')
    trace_factory.get_trace().url_patterns_to_ignore = set()
    assert not epsagon.wrappers.http_filters.is_payload_collection_blacklisted('http://www.test.net')
    assert not epsagon.wrappers.http_filters.is_payload_collection_blacklisted('http://www.bla.test.net')
