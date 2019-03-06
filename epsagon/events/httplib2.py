"""
httplib2 events module.
"""

from __future__ import absolute_import
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse
import traceback
from uuid import uuid4
import simplejson as json

from epsagon.utils import add_data_if_needed
from ..trace import tracer
from ..event import BaseEvent
from ..wrappers.http_filters import is_blacklisted_url
from ..utils import update_api_gateway_headers


class Httplib2Event(BaseEvent):
    """
    Represents base gttplib2 event.
    """

    ORIGIN = 'httplib2'
    RESOURCE_TYPE = 'http'

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

        super(Httplib2Event, self).__init__(start_time)
        self.event_id = 'httplib2-{}'.format(str(uuid4()))

        # Params can be set via args or kwargs.
        url, method, body, headers = Httplib2Event.unroller(*args, **kwargs)

        url_obj = urlparse(url)
        self.resource['name'] = url_obj.hostname
        self.resource['operation'] = method
        self.resource['metadata']['url'] = url

        if headers:
            add_data_if_needed(
                self.resource['metadata'],
                'request_headers',
                headers
            )

        try:
            if body:
                add_data_if_needed(
                    self.resource['metadata'],
                    'request_body',
                    json.loads(body)
                )
        except (TypeError, json.errors.JSONDecodeError):
            # Skip if it is not a JSON body
            pass

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

        response_headers, response_body = response

        self.resource['metadata']['status'] = int(response_headers['status'])
        self.resource = update_api_gateway_headers(
            self.resource,
            response_headers
        )

        add_data_if_needed(
            self.resource['metadata'],
            'response_headers',
            dict(response_headers)
        )

        # Extract only json responses
        try:
            if response_body:
                add_data_if_needed(
                    self.resource['metadata'],
                    'response_body',
                    json.loads(response_body)
                )
        except (TypeError, json.errors.JSONDecodeError):
            # Skip if it is not a JSON body
            pass

        # Detect errors based on status code
        if int(response_headers['status']) >= 300:
            self.set_error()

    @staticmethod
    def unroller(uri='N/A', method='N/A', body=None, headers=None):
        return uri, method, body, headers


class Httplib2EventFactory(object):
    """
    Factory class, generates Httplib2 event.
    """

    @staticmethod
    def create_event(wrapped, instance, args, kwargs, start_time, response,
                     exception):
        """
        Create an event according to the given api_name.
        """
        url, _, _, _ = Httplib2Event.unroller(*args, **kwargs)

        # Detect if URL is blacklisted, and ignore.
        if is_blacklisted_url(url):
            return

        event = Httplib2Event(
            wrapped,
            instance,
            args,
            kwargs,
            start_time,
            response,
            exception
        )

        tracer.add_event(event)
