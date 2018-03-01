"""
Utilities for Epsagon module.
"""

from __future__ import absolute_import
from .trace import tracer
from six.moves.urllib.parse import urlparse

# Method to URL dict
BLACKLIST_URLS = {
    str.endswith: [
        'epsagon.com',
    ],
    str.__contains__: [
        'accounts.google.com',
    ],
}


def add_data_if_needed(dictionary, name, data):
    """
    Adding data if not metadata only mode.
    :param dictionary: dictionary to add the data to
    :param name: key name
    :param data: value
    :return: None
    """
    dictionary[name] = None
    if not tracer.metadata_only:
        dictionary[name] = data


def is_blacklisted_url(url):
    """
    Return true if URL is blacklisted from inspection.
    :param url: url string
    :return: bool
    """

    url = urlparse(url).netloc

    for method in BLACKLIST_URLS:
        for blacklist_url in BLACKLIST_URLS[method]:
            if method(url, blacklist_url):
                return True
    return False
