"""
Utilities for Epsagon module.
"""

from __future__ import absolute_import
from epsagon.constants import TRACE_COLLECTOR_URL, REGION
from .trace import tracer


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
        collector_url = get_tc_url(use_ssl)
    tracer.initialize(
        token=token,
        app_name=app_name,
        collector_url=collector_url,
        metadata_only=metadata_only,
        use_ssl=use_ssl,
        debug=debug
    )
