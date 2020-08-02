"""
urllib3 events module.
"""

from __future__ import absolute_import

try:
    from urllib.parse import urlparse, urlunparse
except ImportError:
    from urlparse import urlparse, urlunparse
import traceback
from uuid import uuid4

from epsagon.utils import add_data_if_needed
from ..trace import trace_factory
from ..event import BaseEvent
from ..http_filters import (
    is_blacklisted_url,
    is_payload_collection_blacklisted
)
from ..utils import update_http_headers, normalize_http_url
from ..constants import HTTP_ERR_CODE, EPSAGON_MARKER


class Urllib3Event(BaseEvent):
    """
    Represents base requests event.
    """

    ORIGIN = 'urllib3'
    RESOURCE_TYPE = 'http'

    # pylint: disable=W0613
    def __init__(self, wrapped, instance, args, kwargs, start_time, response,
                 exception):
        """
        Initialize.
        :param wrapped: wrapt's wrapped
        :param instance: wrapt's instance
        :param args: wrapt's args
        :param kwargs: wrapt's kwargs
        :param start_time: Start timestamp (epoch)
        :param response: response data
        :param exception: Exception (if happened)
        """
        super(Urllib3Event, self).__init__(start_time)

        self.event_id = 'urllib3-{}'.format(str(uuid4()))

        method, url = args
        body = kwargs.get('body')
        headers = kwargs.get('headers')
        if headers:
            # Make sure trace ID is present in case headers will be removed.
            epsagon_trace_id = headers.get('epsagon-trace-id')
            if epsagon_trace_id:
                self.resource['metadata']['http_trace_id'] = epsagon_trace_id

        parsed_url = urlparse(url)
        # Omitting ports (`:80'/':443') for the host URL.
        host_url = parsed_url.netloc.split(':')[0]
        full_url = urlunparse((
            parsed_url.scheme,
            host_url,
            parsed_url.path,
            parsed_url.params,
            parsed_url.query,
            parsed_url.fragment,
        ))

        self.resource['name'] = normalize_http_url(url)
        self.resource['operation'] = method
        self.resource['metadata']['url'] = full_url

        if not is_payload_collection_blacklisted(full_url):
            add_data_if_needed(
                self.resource['metadata'],
                'request_headers',
                dict(headers)
            )

            add_data_if_needed(
                self.resource['metadata'],
                'request_body',
                body
            )

        if response is not None:
            self.update_response(response)

        if exception is not None:
            self.set_exception(exception, traceback.format_exc())

    def update_response(self, response):
        """
        Adds response data to event.
        :param response: Response from botocore
        :return: None
        """
        self.resource['metadata']['status_code'] = response.status
        headers = dict(response.getheaders())
        self.resource = update_http_headers(
            self.resource,
            headers
        )

        self.resource['metadata']['response_body'] = None
        full_url = self.resource['metadata']['url']

        if not is_payload_collection_blacklisted(full_url):
            add_data_if_needed(
                self.resource['metadata'],
                'response_headers',
                headers
            )

        # Detect errors based on status code
        if response.status >= HTTP_ERR_CODE:
            self.set_error()


class Urllib3EventFactory(object):
    """
    Factory class, generates urllib3 event.
    """

    @staticmethod
    def create_event(wrapped, instance, args, kwargs, start_time, response,
                     exception):
        """
        Create an event according to the given api_name.
        """
        # Ignore requests events since they are being instrumented.
        is_requests = (
            str(kwargs.get('headers', {}).get('User-Agent', '')).startswith(
                'python-requests'
            )
        )
        if is_requests or getattr(instance, EPSAGON_MARKER, False):
            return

        path = args[1] if len(args) > 1 else kwargs.get('url', '')
        port_part = ':' + str(instance.port) if instance.port else ''
        host_url = '{}://{}'.format(instance.scheme, instance.host)
        url = '{}{}{}'.format(
            host_url, port_part, path
        )
        args = (args[0] if args else kwargs.get('method', 'UNKNOWN METHOD'),
                url)

        # Detect if URL is blacklisted, and ignore.
        if is_blacklisted_url(host_url):
            return

        event = Urllib3Event(
            wrapped,
            instance,
            args,
            kwargs,
            start_time,
            response,
            exception
        )

        trace_factory.add_event(event)
