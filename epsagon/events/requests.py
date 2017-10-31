"""
requests events module
"""
from __future__ import absolute_import
from urlparse import urlparse
from uuid import uuid4
from ..common import ErrorCode
from ..trace import tracer
from ..event import BaseEvent


class RequestsEvent(BaseEvent):
    """
    Represents base requests event
    """

    EVENT_MODULE = 'requests'
    EVENT_TYPE = 'requests'

    def __init__(self, args):
        super(RequestsEvent, self).__init__()
        # Most APIs requests don't have ids so we generate one
        self.event_id = 'r{}'.format(str(uuid4()))
        self.resource_name = self.EVENT_TYPE

        prepared_request = args[0]

        self.metadata = {
            'method': prepared_request.method,
            'url': prepared_request.url,
            'request_body': prepared_request.body,
        }

    def set_error(self):
        tracer.error_code = ErrorCode.ERROR
        self.error_code = ErrorCode.ERROR

    def post_update(self, response):
        self.metadata['status_code'] = response.status_code
        self.metadata['response_headers'] = dict(response.headers)

        # Extract only json responses
        self.metadata['response_body'] = ''
        try:
            self.metadata['response_body'] = response.json()
        except ValueError:
            pass

        # Detect errors based on status code
        if response.status_code >= 300:
            self.set_error()


class RequestsAuth0Event(RequestsEvent):
    """
    Represents auth0 requests event
    """

    EVENT_TYPE = 'auth0'

    def __init__(self, args):
        super(RequestsAuth0Event, self).__init__(args)
        prepared_request = args[0]
        self.event_operation = prepared_request.path_url.split('/')[-1]


class RequestsTwilioEvent(RequestsEvent):
    """
    Represents Twilio requests event
    """

    EVENT_TYPE = 'twilio'

    def __init__(self, args):
        super(RequestsTwilioEvent, self).__init__(args)


class RequestsEventFactory(object):

    FACTORY_DICT = {
        RequestsAuth0Event.EVENT_TYPE: RequestsAuth0Event,
        RequestsTwilioEvent.EVENT_TYPE: RequestsTwilioEvent,
    }

    @staticmethod
    def factory(args):
        prepared_request = args[0]
        base_url = urlparse(prepared_request.url).netloc

        # Start with base event
        instance_type = RequestsEvent

        # Look for API matching in url
        for api_name in RequestsEventFactory.FACTORY_DICT:
            if api_name in base_url:
                instance_type = RequestsEventFactory.FACTORY_DICT[api_name]

        return instance_type(args)
