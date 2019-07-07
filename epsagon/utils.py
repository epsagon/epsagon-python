"""
Utilities for Epsagon module.
"""

from __future__ import absolute_import
import os
from epsagon.constants import TRACE_COLLECTOR_URL, REGION
from .trace import trace_factory
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
    if not trace_factory.metadata_only:
        dictionary[name] = data


def update_api_gateway_headers(resource_data, response_headers):
    """
    Updates resource data dict with API Gateway if matching header found.
    :param resource_data: event's resource data dict
    :param response_headers: response headers from HTTP request
    :return: update resource data dict
    """
    for header_key, header_value in response_headers.items():
        if header_key.lower() == 'x-amzn-requestid':
            # This is a request to AWS API Gateway
            resource_data['type'] = 'api_gateway'
            resource_data['metadata']['request_trace_id'] = header_value
            break

    return resource_data


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
    disable_timeout_send=False,
    use_ssl=True,
    debug=False,
    send_trace_only_on_error=False,
    url_patterns_to_ignore=None,
    keys_to_ignore=None
):
    """
    Initializes trace with user's data.
    User can configure here trace parameters.
    :param token: user's token
    :param app_name: application name
    :param collector_url: the url of the collector.
    :param metadata_only: whether to send only the metadata, or also the data.
    :param disable_timeout_send: whether to disable traces send on timeout
     (when enabled, is t done using a signal handler).
    :param use_ssl: whether to use SSL or not.
    :param debug: debug mode flag,
    :param send_trace_only_on_error: Whether to send trace only when
     there is an error or not.
    :param url_patterns_to_ignore: URL patterns to ignore in HTTP data
      collection.
    :param keys_to_ignore: List of keys to ignore while extracting metadata.
    :return: None
    """
    if not collector_url:
        collector_url = get_tc_url(
            ((os.getenv('EPSAGON_SSL') or '').upper() == 'TRUE') | use_ssl
        )
    # Ignored URLs is a comma separated values, if coming from env.
    ignored_urls = os.getenv('EPSAGON_URLS_TO_IGNORE')
    if ignored_urls:
        ignored_urls = ignored_urls.split(',')

    # Same goes for Ignored keys.
    ignored_keys = os.getenv('EPSAGON_IGNORED_KEYS')
    if ignored_keys:
        ignored_keys = ignored_keys.split(',')

    trace_factory.initialize(
        token=os.getenv('EPSAGON_TOKEN') or token,
        app_name=os.getenv('EPSAGON_APP_NAME') or app_name,
        collector_url=os.getenv('EPSAGON_COLLECTOR_URL') or collector_url,
        metadata_only=(
          ((os.getenv('EPSAGON_METADATA') or '').upper() == 'TRUE') |
          metadata_only
        ),
        disable_timeout_send=(
            ((os.getenv('EPSAGON_DISABLE_ON_TIMEOUT') or '').upper() == 'TRUE')
            | disable_timeout_send
        ),
        debug=((os.getenv('EPSAGON_DEBUG') or '').upper() == 'TRUE') | debug,
        send_trace_only_on_error=(
            ((os.getenv('EPSAGON_SEND_TRACE_ON_ERROR') or '').upper() == 'TRUE')
            | send_trace_only_on_error
        ),
        url_patterns_to_ignore=ignored_urls or url_patterns_to_ignore,
        keys_to_ignore=ignored_keys or keys_to_ignore,
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
