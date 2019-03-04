"""
requests events module.
"""

from __future__ import absolute_import
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse
import traceback
from uuid import uuid4

from epsagon.utils import add_data_if_needed
from ..trace import tracer
from ..event import BaseEvent
from ..wrappers.http_filters import is_blacklisted_url
from ..utils import update_api_gateway_headers


class RequestsEvent(BaseEvent):
    """
    Represents base requests event.
    """

    ORIGIN = 'requests'
    RESOURCE_TYPE = 'requests'

    #pylint: disable=W0613
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

        super(RequestsEvent, self).__init__(start_time)

        self.event_id = 'requests-{}'.format(str(uuid4()))

        prepared_request = args[0]
        url_obj = urlparse(prepared_request.url)
        self.resource['name'] = url_obj.hostname
        self.resource['operation'] = prepared_request.method
        self.resource['metadata']['url'] = prepared_request.url

        add_data_if_needed(
            self.resource['metadata'],
            'request_headers',
            dict(prepared_request.headers)
        )

        add_data_if_needed(
            self.resource['metadata'],
            'request_body',
            prepared_request.body
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

        self.resource['metadata']['status_code'] = response.status_code
        self.resource = update_api_gateway_headers(
            self.resource,
            response.headers
        )

        add_data_if_needed(
            self.resource['metadata'],
            'response_headers',
            dict(response.headers)
        )

        # Extract only json responses
        self.resource['metadata']['response_body'] = None
        try:
            add_data_if_needed(
                self.resource['metadata'],
                'response_body',
                response.json()
            )
        except ValueError:
            pass

        # Detect errors based on status code
        if response.status_code >= 300:
            self.set_error()


class RequestsEventFactory(object):
    """
    Factory class, generates requests event.
    """

    @staticmethod
    def create_event(wrapped, instance, args, kwargs, start_time, response,
                     exception):
        """
        Create an event according to the given api_name.
        """
        prepared_request = args[0]

        # Detect if URL is blacklisted, and ignore.
        if is_blacklisted_url(prepared_request.url):
            return

        event = RequestsEvent(
            wrapped,
            instance,
            args,
            kwargs,
            start_time,
            response,
            exception
        )

        tracer.add_event(event)
