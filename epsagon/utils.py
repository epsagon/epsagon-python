"""
Utilities for Epsagon module.
"""

from __future__ import absolute_import
from six.moves import urllib
from .trace import tracer


# Method to URL dict.
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
    Add data to the given dictionary if metadata_only option is set to False.
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
