"""
Utils for web frameworks request filters.
"""

from six.moves import urllib
from epsagon.trace import trace_factory
from epsagon.constants import IGNORED_ENDPOINTS

# Ignored content types for web frameworks.
IGNORED_CONTENT_TYPES = [
    'image',
    'audio',
    'video',
    'font',
    'zip',
    'css',
]
IGNORED_FILE_TYPES = [
    '.js',
    '.jsx',
    '.woff',
    '.woff2',
    '.ttf',
    '.eot',
    '.ico',
]

FILE_PREFIX = 'file://'

# Method to URL dict.
BLACKLIST_URLS = {
    str.endswith: [
        'tc.epsagon.com',
        '.amazonaws.com',
        '.myqcloud.com',
    ],
    str.__contains__: [
        'accounts.google.com',
        'documents.azure.com',
        '169.254.170.2'  # AWS Task Metadata Endpoint
    ],
}
WHITELIST_URL = {
    str.__contains__: [
        '.execute-api.',
        '.elb.amazonaws.com',
        '.appsync-api.',
    ],
}


def is_blacklisted_url(url):
    """
    Return whether the URL blacklisted or not.
    Using BLACKLIST_URLS methods against the URLs.
    :param url: url string
    :return: True if URL is blacklisted, else False
    """
    if url.startswith(FILE_PREFIX):
        return True

    url = urllib.parse.urlparse(url).netloc
    for method in WHITELIST_URL:
        for whitelist_url in WHITELIST_URL[method]:
            if method(url, whitelist_url):
                return False

    for method in BLACKLIST_URLS:
        for blacklist_url in BLACKLIST_URLS[method]:
            if method(url, blacklist_url):
                return True

    return False


def is_payload_collection_blacklisted(url):
    """
    Return whether the payload should be collected according to the blacklisted
    urls list in the Trace.
    :param url: url string
    :return:  True if URL is blacklisted, else False
    """
    url = urllib.parse.urlparse(url).netloc
    if trace_factory.get_trace():
        trace_blacklist_urls = trace_factory.get_trace().url_patterns_to_ignore
    else:
        trace_blacklist_urls = tuple()
    return any(blacklist_url in url for blacklist_url in trace_blacklist_urls)


def ignore_request(content, path):
    """
    Return true if HTTP request in web frameworks should be omitted.
    :param content: accept mimetype header
    :param path: request path
    :return: Bool
    """

    return (
        any([x in content for x in IGNORED_CONTENT_TYPES]) or
        any([path.endswith(x) for x in IGNORED_FILE_TYPES])
    )


def add_ignored_endpoints(endpoints):
    """
    add endpoints to the list of ignored ones..
    :param endpoints: list of endpoints or None
    :return: None
    """
    if endpoints:
        IGNORED_ENDPOINTS.extend(endpoints)


def is_ignored_endpoint(endpoint):
    """
    return true if endpoint should be ignored.
    :param endpoint: endpoint path
    :return: Bool
    """
    return endpoint in IGNORED_ENDPOINTS
