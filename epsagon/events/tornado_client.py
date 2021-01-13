"""
Tornado AsyncHTTPClient events module.
"""

from __future__ import absolute_import

import functools
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
from ..constants import HTTP_ERR_CODE, EPSAGON_HEADER_TITLE


class TornadoAsyncHTTPClientEvent(BaseEvent):
    """
    Represents base request event.
    """

    ORIGIN = 'tornado_client'
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
        super(TornadoAsyncHTTPClientEvent, self).__init__(start_time)
        self.event_id = 'tornado-client-{}'.format(str(uuid4()))

        request = args[0]
        headers = dict(request.headers)
        if headers:
            # Make sure trace ID is present in case headers will be removed.
            epsagon_trace_id = headers.get(EPSAGON_HEADER_TITLE)
            if epsagon_trace_id:
                self.resource['metadata']['http_trace_id'] = epsagon_trace_id

        parsed_url = urlparse(request.url)

        host_url = parsed_url.netloc.split(':')[0]
        full_url = urlunparse((
            parsed_url.scheme,
            host_url,
            parsed_url.path,
            parsed_url.params,
            parsed_url.query,
            parsed_url.fragment,
        ))

        self.resource['name'] = normalize_http_url(request.url)
        self.resource['operation'] = request.method
        self.resource['metadata']['url'] = request.url

        if not is_payload_collection_blacklisted(full_url):
            add_data_if_needed(
                self.resource['metadata'],
                'request_headers',
                headers
            )
            body = request.body
            if isinstance(body, bytes):
                body = body.decode('utf-8')
            if body:
                add_data_if_needed(
                    self.resource['metadata'],
                    'request_body',
                    body
                )

        if response is not None:
            callback = functools.partial(self.update_response)
            response.add_done_callback(callback)

        if exception is not None:
            self.set_exception(exception, traceback.format_exc())

    def update_response(self, future):
        """
        Adds response data to event.
        :param future: Future response object
        :return: None
        """
        response = future.result()

        self.resource['metadata']['status_code'] = response.code
        self.resource = update_http_headers(
            self.resource,
            dict(response.headers)
        )

        full_url = self.resource['metadata']['url']

        if not is_payload_collection_blacklisted(full_url):
            add_data_if_needed(
                self.resource['metadata'],
                'response_headers',
                dict(response.headers)
            )
            body = response.body
            if isinstance(body, bytes):
                try:
                    body = body.decode('utf-8')
                except UnicodeDecodeError:
                    body = str(body)
            if body:
                add_data_if_needed(
                    self.resource['metadata'],
                    'response_body',
                    body
                )

        # Detect errors based on status code
        if response.code >= HTTP_ERR_CODE:
            self.set_error()


class TornadoClientEventFactory(object):
    """
    Factory class, generates AsyncHTTPClient event.
    """

    @staticmethod
    def create_event(wrapped, instance, args, kwargs, start_time, response,
                     exception):
        """
        Create an AsyncHTTPClient event.
        """
        # Detect if URL is blacklisted, and ignore.
        if is_blacklisted_url(args[0].url):
            return

        event = TornadoAsyncHTTPClientEvent(
            wrapped,
            instance,
            args,
            kwargs,
            start_time,
            response,
            exception
        )

        trace_factory.add_event(event)
