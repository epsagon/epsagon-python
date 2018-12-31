"""
Utilities for Epsagon module.
"""

from __future__ import absolute_import
import os
from six.moves import urllib

from epsagon.constants import TRACE_COLLECTOR_URL, REGION
from .trace import tracer
from .constants import EPSAGON_HANDLER

# Method to URL dict.
BLACKLIST_URLS = {
    str.endswith: [
        'epsagon.com',
    ],
    str.__contains__: [
        'accounts.google.com',
    ],
}


def get_env_or_val(env_key, value):
    """
    return environment variable if exists, otherwise value.
    :param env_key: environment key
    :param value: value
    :return: env or value
    """
    return os.getenv(env_key) if os.getenv(env_key) else value


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
    protocol = 'https://' if use_ssl else 'http://'

    return TRACE_COLLECTOR_URL.format(protocol=protocol, region=REGION)


def init(
    token='',
    app_name='default',
    collector_url=None,
    metadata_only=True,
    use_ssl=True,
    debug=False
):
    """
    Initializes trace with user's data.
    User can configure here trace parameters.
    :param token: user's token
    :param app_name: application name
    :param collector_url: the url of the collector.
    :param metadata_only: whether to send only the metadata, or also the data.
    :param use_ssl: whether to use SSL or not.
    :param debug: debug mode flag
    :return: None
    """
    if not collector_url:
        collector_url = get_tc_url(
            (get_env_or_val('EPSAGON_SSL', '') == 'TRUE') | use_ssl
        )
    tracer.initialize(
        token=get_env_or_val('EPSAGON_TOKEN', token),
        app_name=get_env_or_val('EPSAGON_APP_NAME', app_name),
        collector_url=get_env_or_val('EPSAGON_COLLECTOR_URL', collector_url),
        metadata_only=(
          (get_env_or_val('EPSAGON_METADATA', '') == 'TRUE') | metadata_only
        ),
        debug=(get_env_or_val('EPSAGON_DEBUG', '') == 'TRUE') | debug
    )


def import_original_module():
    """
    Imports original module
    :return:
    """
    original_handler = os.getenv(EPSAGON_HANDLER)
    if not original_handler:
        raise ValueError(
            'EPSAGON_HANDLER value not specified in environment variable'
        )

    try:
        module_path, handler_name = original_handler.rsplit('.', 1)
    except ValueError:
        raise ValueError('wrong handler formatted: {}'.format(original_handler))

    module_path = module_path.replace('/', '.')

    try:
        return __import__(module_path), module_path, handler_name
    except ImportError:
        raise ImportError('Failed to import module: {}'.format(module_path))
