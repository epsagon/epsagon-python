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
from six.moves import urllib

from epsagon.utils import add_data_if_needed
from ..trace import tracer
from ..event import BaseEvent
from ..utils import is_blacklisted_url


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
        self.resource['name'] = self.RESOURCE_TYPE

        prepared_request = args[0]
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
        if 'x-amzn-requestid' in response.headers:
            # This is a request to AWS API Gateway
            url = urlparse(self.resource['metadata']['url'])
            self.resource['type'] = 'api_gateway'
            self.resource['name'] = url.path
            self.resource['metadata']['request_trace_id'] = (
                response.headers['x-amzn-requestid']
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


class RequestsAuth0Event(RequestsEvent):
    """
    Represents auth0 requests event.
    """

    RESOURCE_TYPE = 'auth0'
    API_TAG = '/api/v2/'

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

        super(RequestsAuth0Event, self).__init__(
            wrapped,
            instance,
            args,
            kwargs,
            start_time,
            response,
            exception
        )

        prepared_request = args[0]
        url = prepared_request.path_url
        self.resource['metadata']['endpoint'] = \
            url[url.find(self.API_TAG) + len(self.API_TAG):]


class RequestsTwilioEvent(RequestsEvent):
    """
    Represents Twilio requests event.
    """

    RESOURCE_TYPE = 'twilio'

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

        super(RequestsTwilioEvent, self).__init__(
            wrapped,
            instance,
            args,
            kwargs,
            start_time,
            response,
            exception
        )

        prepared_request = args[0]
        self.resource['metadata']['endpoint'] = \
            prepared_request.path_url.split('/')[-1]


class RequestsEventFactory(object):
    """
    Factory class, generates requests event.
    """

    FACTORY = {
        class_obj.RESOURCE_TYPE: class_obj
        for class_obj in RequestsEvent.__subclasses__()
    }

    @staticmethod
    def create_event(wrapped, instance, args, kwargs, start_time, response,
                     exception):
        """
        Create an event according to the given api_name.
        :param wrapped:
        :param instance:
        :param args:
        :param kwargs:
        :param start_time:
        :param response:
        :param exception:
        :return:
        """
        prepared_request = args[0]

        # Detect if URL is blacklisted, and ignore.
        if is_blacklisted_url(prepared_request.url):
            return

        base_url = urllib.parse.urlparse(prepared_request.url).netloc

        # Start with base event
        instance_type = RequestsEvent

        # Look for API matching in url
        for api_name in RequestsEventFactory.FACTORY:
            if api_name in base_url.lower():
                instance_type = RequestsEventFactory.FACTORY[api_name]

        event = instance_type(
            wrapped,
            instance,
            args,
            kwargs,
            start_time,
            response,
            exception
        )

        tracer.add_event(event)
