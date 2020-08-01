"""
Utilities for Epsagon module.
"""

from __future__ import absolute_import, print_function
import os
import collections
import socket
import sys
import traceback
import re
import six
import requests
import simplejson as json
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

from epsagon import http_filters
from epsagon.constants import TRACE_COLLECTOR_URL, REGION
from .trace import trace_factory, create_transport
from .constants import EPSAGON_HANDLER, DEBUG_MODE, DEFAULT_SAMPLE_RATE


METADATA_CACHE = {
    'queried': False,
    'data': {},
}


def normalize_http_url(url):
    """
    Strip http schema, port number and path from a url
    :param url: the url to normalize
    :return: normalized url
    """
    parsed = urlparse(url)
    netloc = parsed.netloc
    return netloc.split(':')[0] if netloc else url


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


def update_http_headers(resource_data, response_headers):
    """
    Updates resource data dict with AWS entities if matching header found.
    :param resource_data: event's resource data dict
    :param response_headers: response headers from HTTP request
    :return: update resource data dict
    """
    for header_key, header_value in response_headers.items():
        if header_key.lower() == 'x-amzn-requestid':
            # This is a request to API Gateway
            if '.appsync-api.' not in resource_data['metadata']['url']:
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
    app_name='Application',
    collector_url=None,
    metadata_only=True,
    disable_timeout_send=False,
    use_ssl=True,
    debug=False,
    send_trace_only_on_error=False,
    url_patterns_to_ignore=None,
    keys_to_ignore=None,
    keys_to_allow=None,
    ignored_endpoints=None,
    split_on_send=False,
    propagate_lambda_id=False,
    logging_tracing_enabled=True,
    step_dict_output_path=None,
    sample_rate=DEFAULT_SAMPLE_RATE,
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
    :param keys_to_allow: List of keys to allow while extracting metadata
    :param ignored_endpoints: List of ignored endpoints for web frameworks.
    :param split_on_send: Split the trace on send flag
    :param propagate_lambda_id: Inject identifiers via return value flag
    :param logging_tracing_enabled: Add an epsagon log id to logging calls
    :param step_dict_output_path:
        Path in the result dict to append the Epsagon steps data
    :param sample_rate: A number between 0 and 1, represents the probability
        of a trace to be sent.
        When enabled (value < 1), sampling will be performed according to
        the given value.
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

    # Ignored URLs is a comma separated values, if coming from env.
    ignored_paths = os.getenv('EPSAGON_ENDPOINTS_TO_IGNORE')
    if ignored_paths:
        ignored_paths = ignored_paths.split(',')

    # Same goes for Ignored keys.
    ignored_keys = os.getenv('EPSAGON_IGNORED_KEYS')
    if ignored_keys:
        ignored_keys = ignored_keys.split(',')

    allowed_keys = os.getenv('EPSAGON_ALLOWED_KEYS')
    if allowed_keys:
        allowed_keys = allowed_keys.split(',')

    step_dict_output_path_env = os.getenv('EPSAGON_STEPS_OUTPUT_PATH')
    if step_dict_output_path_env:
        step_dict_output_path_env = step_dict_output_path_env.split('.')

    # If EPSAGON_METADATA exists as an env var - use it
    if os.getenv('EPSAGON_METADATA'):
        metadata_only = (os.getenv('EPSAGON_METADATA') or '').upper() == 'TRUE'

    # If EPSAGON_LOGGING_TRACING_ENABLED exists as an env var - use it
    if os.getenv('EPSAGON_LOGGING_TRACING_ENABLED'):
        logging_tracing_enabled = (
            os.getenv('EPSAGON_LOGGING_TRACING_ENABLED') or ''
        ).upper() == 'TRUE'

    # In case we're running on AWS Lambda, logging correlation is disabled
    if is_lambda_env():
        logging_tracing_enabled = False

    if os.getenv('EPSAGON_SAMPLE_RATE'):
        sample_rate = float(os.getenv('EPSAGON_SAMPLE_RATE'))

    trace_factory.initialize(
        token=os.getenv('EPSAGON_TOKEN') or token,
        app_name=os.getenv('EPSAGON_APP_NAME') or app_name,
        collector_url=os.getenv('EPSAGON_COLLECTOR_URL') or collector_url,
        metadata_only=metadata_only,
        disable_timeout_send=(
            ((os.getenv('EPSAGON_DISABLE_ON_TIMEOUT') or '')
                .upper() == 'TRUE')
            | disable_timeout_send
        ),
        debug=((os.getenv('EPSAGON_DEBUG') or '')
               .upper() == 'TRUE') | debug,
        send_trace_only_on_error=(
            ((os.getenv('EPSAGON_SEND_TRACE_ON_ERROR') or '')
                .upper() == 'TRUE')
            | send_trace_only_on_error
        ),
        url_patterns_to_ignore=ignored_urls or url_patterns_to_ignore,
        keys_to_ignore=ignored_keys or keys_to_ignore,
        keys_to_allow=allowed_keys or keys_to_allow,
        transport=create_transport(collector_url, token),
        split_on_send=(
                ((os.getenv('EPSAGON_SPLIT_ON_SEND') or '').upper() == 'TRUE')
                | split_on_send
        ),
        propagate_lambda_id=(
                ((os.getenv('EPSAGON_PROPAGATE_LAMBDA_ID') or '').upper() ==
                 'TRUE')
                | propagate_lambda_id
        ),
        logging_tracing_enabled=logging_tracing_enabled,
        step_dict_output_path=(
            step_dict_output_path_env or step_dict_output_path
        ),
        sample_rate=sample_rate
    )

    # Append to ignored endpoints
    http_filters.add_ignored_endpoints(ignored_paths or ignored_endpoints)


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


def collect_container_metadata(metadata):
    """
    Collects container metadata if exists.
    :return: dict.
    """
    is_k8s = os.environ.get('KUBERNETES_SERVICE_HOST')
    if is_k8s:
        metadata['is_k8s'] = True
        metadata['k8s_pod_name'] = socket.gethostname()
        with open('/proc/self/cgroup', 'r') as proc_file:
            metadata['k8s_container_id'] = (
                proc_file.readline().split('/')[-1].rstrip('\n')
            )

    if METADATA_CACHE['queried'] and METADATA_CACHE['data']:
        metadata['ECS'] = METADATA_CACHE['data']
        return

    METADATA_CACHE['queried'] = True
    metadata_uri = os.environ.get('ECS_CONTAINER_METADATA_URI')
    if not metadata_uri:
        return
    container_metadata = json.loads(requests.get(metadata_uri).content)

    new_metadata = container_metadata['Labels'].copy()
    new_metadata['Limits'] = container_metadata['Limits']
    METADATA_CACHE['data'] = new_metadata
    if METADATA_CACHE['data']:
        metadata['ECS'] = METADATA_CACHE['data']


def find_in_object(obj, key, path=None):
    """
    recursively search for a key in an object
    :param obj: The dict to search in
    :param key: The key to search for
    :param path: The path (as an array) of the key nested in the object
    :return: The value and path of this key in the object,
        or None if was not found
    """
    if not path:
        path = []

    if isinstance(obj, collections.Mapping):
        # search key in obj
        if key in obj:
            return obj[key], path

    if (
        isinstance(obj, collections.Iterable)
        and not isinstance(obj, six.string_types)
    ):
        for k in obj:
            # Handle lists as well
            element = k if isinstance(obj, list) else obj[k]
            nested_path = None if isinstance(obj, list) else path + [k]
            result = find_in_object(element, key, nested_path)
            if result:
                return result

    return None

def collect_exception_python3(exception):
    """
    Collect exception from exception __traceback__.
    :param exception: Exception from Flask.
    :return: traceback data
    """

    traceback_data = ''.join(traceback.format_exception(
        type(exception),
        exception,
        exception.__traceback__,
    ))
    return traceback_data


def collect_exception_python2():
    """
    Collect exception from exception sys.exc_info.
    :return: traceback data
    """

    traceback_data = six.StringIO()
    traceback.print_exception(*sys.exc_info(), file=traceback_data)
    return traceback_data.getvalue()


def get_traceback_data_from_exception(exception):
    """
    Get traceback data from exception
    :param exception: the Exception
    :return: traceback data
    """
    python_version = sys.version_info.major
    if python_version == 2:
        return collect_exception_python2()
    if python_version == 3:
        return collect_exception_python3(exception)
    return ''


def parse_json(json_string):
    """
    Parse JSON string to a Python Dictionary
    :param json_string: JSON string
    :return: Python Dictionary
    """
    try:
        return json.loads(json_string)
    except ValueError:
        return None


def camel_case_to_title_case(camel_case_string):
    """
    Turn Camel Case string into Title Case string in which first characters of
    all the words are capitalized.
    :param camel_case_string: Camel Case string
    :return: Title Case string
    """
    if not isinstance(camel_case_string, str):
        return None
    title_case = re.sub('([^-])([A-Z][a-z-]+)', r'\1 \2', camel_case_string)\
        .title()
    return title_case


def add_metadata_from_dict(resource, dictionary, key):
    """
    Add new data to resource metadata
    :param resource: Resource
    :param dictionary: Argument Dictionary
    :param key: Property key
    :return: True if added, else False
    """
    value = dictionary.get(key)
    if not value and not isinstance(value, str):
        return
    title_case_key = camel_case_to_title_case(key)
    resource['metadata'][title_case_key] = value


def is_lambda_env():
    """
    Returns True if the current environment is running on a Lambda function.
    :return: bool
    """
    return os.getenv('AWS_LAMBDA_FUNCTION_NAME') is not None


def print_debug(log):
    if DEBUG_MODE:
        print('[EPSAGON_DEBUG]: {}'.format(log))
