"""
Utilities for Epsagon module.
"""

from __future__ import absolute_import
from six.moves import urllib

from epsagon.constants import TRACE_COLLECTOR_URL, REGION
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


def get_tc_url(use_ssl):
    """
    Get the TraceCollector URL.
    :return: TraceCollector URL.
    """
    protocol = "http://"
    if use_ssl:
        protocol = "https://"

    return TRACE_COLLECTOR_URL.format(protocol=protocol, region=REGION)


def init(token,
         app_name='default',
         collector_url=None,
         metadata_only=True,
         use_ssl=False
         ):
    """
    Initializes trace with user's data.
    User can configure here trace parameters.
    :param token: user's token
    :param app_name: application name
    :param collector_url: the url of the collector.
    :param metadata_only: whether to send only the metadata, or also the data.
    :param use_ssl:L whether to use SSL or not.
    :return: None
    """
    if not collector_url:
        collector_url = get_tc_url(use_ssl)
    tracer.initialize(
        token=token,
        app_name=app_name,
        collector_url=collector_url,
        metadata_only=metadata_only,
        use_ssl=use_ssl
    )
