import epsagon.trace
import epsagon.utils
from epsagon.trace import tracer


def setup_function(func):
    tracer.__init__()


def test_blacklist_url():
    """
    Test is_blacklisted_url functionality.
    :return: None
    """

    epsagon.utils.BLACKLIST_URLS = {
        str.endswith: [
            '.com',
        ],
        str.__contains__: [
            'restricted',
        ],
    }

    assert epsagon.utils.is_blacklisted_url('http://www.google.com')
    assert epsagon.utils.is_blacklisted_url('https://www.restricted-site.org')
    assert epsagon.utils.is_blacklisted_url('http://www.restricted-site.com')
    assert not epsagon.utils.is_blacklisted_url('https://www.com.org')
    assert not epsagon.utils.is_blacklisted_url('http://www.google.org')


def test_original_blacklist_url():
    """
    Validate original needed URLs are in.
    :return: None
    """

    assert epsagon.utils.is_blacklisted_url('http://tc.us-east-1.epsagon.com')
    assert epsagon.utils.is_blacklisted_url('https://client.tc.epsagon.com')