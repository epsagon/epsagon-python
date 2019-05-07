import epsagon.trace
import epsagon.utils
import epsagon.wrappers.http_filters
from epsagon.trace import factory


def setup_function(func):
    factory.get_trace().__init__()


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