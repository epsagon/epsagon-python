"""
Utils for web frameworks request filters.
"""

from six.moves import urllib

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

# Method to URL dict.
BLACKLIST_URLS = {
    str.endswith: [
        'epsagon.com',
        '.amazonaws.com',
    ],
    str.__contains__: [
        'accounts.google.com',
    ],
}


def is_blacklisted_url(url):
    """
    Return whether the URL blacklisted or not.
    Using BLACKLIST_URLS methods against the URLs.
    :param url: url string
    :return: True if URL is blacklisted, else False
    """

    url = urllib.parse.urlparse(url).netloc

    for method in BLACKLIST_URLS:
        for blacklist_url in BLACKLIST_URLS[method]:
            if method(url, blacklist_url):
                return True
    return False


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
