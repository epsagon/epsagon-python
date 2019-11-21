"""
requests events module.
"""

from __future__ import absolute_import

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
from ..constants import HTTP_ERR_CODE


class UrllibEvent(BaseEvent):
    """
    Represents base requests event.
    """

    ORIGIN = 'urllib'
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

        super(UrllibEvent, self).__init__(start_time)

        self.event_id = 'urllib-{}'.format(str(uuid4()))

        prepared_request, data = args
        self.resource['name'] = normalize_http_url(prepared_request.full_url)
        self.resource['operation'] = prepared_request.get_method()
        self.resource['metadata']['url'] = prepared_request.full_url

        if not is_payload_collection_blacklisted(prepared_request.full_url):
            add_data_if_needed(
                self.resource['metadata'],
                'request_headers',
                dict(prepared_request.headers)
            )

            add_data_if_needed(
                self.resource['metadata'],
                'request_body',
                data
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

            # Extract only json responses
            try:
                add_data_if_needed(
                    self.resource['metadata'],
                    'response_body',
                    str(response.peek())
                )
            except ValueError:
                pass

        # Detect errors based on status code
        if response.status >= HTTP_ERR_CODE:
            self.set_error()


class UrllibEventFactory(object):
    """
    Factory class, generates urllib event.
    """

    @staticmethod
    def create_event(wrapped, instance, args, kwargs, start_time, response,
                     exception):
        """
        Create an event according to the given api_name.
        """
        prepared_request = args[0]

        # Detect if URL is blacklisted, and ignore.
        if is_blacklisted_url(prepared_request.full_url):
            return

        event = UrllibEvent(
            wrapped,
            instance,
            args,
            kwargs,
            start_time,
            response,
            exception
        )

        trace_factory.add_event(event)
