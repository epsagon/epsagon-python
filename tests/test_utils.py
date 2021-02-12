import epsagon.trace
import epsagon.utils
import epsagon.http_filters
from epsagon.trace import trace_factory
from epsagon.constants import OBFUSCATION_MASK


def setup_function(func):
    trace_factory.get_or_create_trace()


def test_blacklist_url():
    """
    Test is_blacklisted_url functionality.
    :return: None
    """

    epsagon.http_filters.BLACKLIST_URLS = {
        str.endswith: [
            '.com',
        ],
        str.__contains__: [
            'restricted',
        ],
    }

    assert epsagon.http_filters.is_blacklisted_url('http://www.google.com')
    assert epsagon.http_filters.is_blacklisted_url('https://www.restricted-site.org')
    assert epsagon.http_filters.is_blacklisted_url('http://www.restricted-site.com')
    assert not epsagon.http_filters.is_blacklisted_url('https://www.com.org')
    assert not epsagon.http_filters.is_blacklisted_url('http://www.google.org')


def test_original_blacklist_url():
    """
    Validate original needed URLs are in.
    :return: None
    """

    assert epsagon.http_filters.is_blacklisted_url('http://tc.us-east-1.epsagon.com')
    assert epsagon.http_filters.is_blacklisted_url('https://client.tc.epsagon.com')


def test_trace_blacklist():
    """
    Validate trace URL Blacklist mechanism.
    :return: None
    """
    trace_factory.get_trace().url_patterns_to_ignore = set(('test.net', 'test2.net'))
    assert epsagon.http_filters.is_payload_collection_blacklisted('http://www.test.net')
    assert epsagon.http_filters.is_payload_collection_blacklisted('http://www.bla.test.net')
    assert not epsagon.http_filters.is_payload_collection_blacklisted('http://www.test.new.net')
    trace_factory.get_trace().url_patterns_to_ignore = set()
    assert not epsagon.http_filters.is_payload_collection_blacklisted('http://www.test.net')
    assert not epsagon.http_filters.is_payload_collection_blacklisted('http://www.bla.test.net')

def test_obfuscate_sql():
    """
    Validate SQL Query Obfuscation
    :return: None
    """
    assert epsagon.utils.obfuscate_sql_query(
        "INSERT "
        "   INTO people "
        "   VALUES ('Mahatma', 'Ghandi', 78);",
        'insert',
    ).count(OBFUSCATION_MASK) == 3

    assert epsagon.utils.obfuscate_sql_query(
        "SELECT * "
        "   FROM people "
        "   WHERE first = 'Mahatma' AND last = 'Ghandi' OR age>=78 "
        "   GROUP BY first, last, age ORDER BY age;",
        'select',
    ).count(OBFUSCATION_MASK) == 3

    assert epsagon.utils.obfuscate_sql_query(
        "SELECT Count(*) "
        "   FROM people "
        "   WHERE first='M' OR first NOT IN "
        "       (SELECT last FROM people WHERE age =30 AND last='F') "
        "   AND NOT EXISTS "
        "       (SELECT age FROM people WHERE first='J');",
        'select',
    ).count(OBFUSCATION_MASK) == 4

    assert epsagon.utils.obfuscate_sql_query(
        "SELECT * "
        "   FROM people p "
        "   INNER JOIN people pp on p.age = pp.age "
        "   WHERE p.age >=78;",
        'select',
    ).count(OBFUSCATION_MASK) == 1