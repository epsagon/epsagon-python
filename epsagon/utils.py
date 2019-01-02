"""
Utilities for Epsagon module.
"""

from __future__ import absolute_import
import os
from six.moves import urllib
from epsagon.constants import TRACE_COLLECTOR_URL, REGION
from .trace import tracer
from .constants import EPSAGON_HANDLER


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
            ((os.getenv('EPSAGON_SSL') or '') == 'TRUE') | use_ssl
        )
    tracer.initialize(
        token=os.getenv('EPSAGON_TOKEN') or token,
        app_name=os.getenv('EPSAGON_APP_NAME') or app_name,
        collector_url=os.getenv('EPSAGON_COLLECTOR_URL') or collector_url,
        metadata_only=(
          ((os.getenv('EPSAGON_METADATA') or '') == 'TRUE') | metadata_only
        ),
        debug=((os.getenv('EPSAGON_DEBUG') or '') == 'TRUE') | debug
    )


def import_original_module():
    """
    Imports original user's handler using the `EPSAGON_HANDLER` env.
    :return: Module or Exception
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
