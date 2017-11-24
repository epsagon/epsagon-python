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
        self.event_id = 'requests-{}'.format(str(uuid4()))
        self.resource_name = self.EVENT_TYPE

        prepared_request = args[0]
        self.event_operation = prepared_request.method

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
        self.metadata['response_body'] = None
        try:
            self.metadata['response_body'] = response.json()
        except ValueError:
            pass

        # Detect errors based on status code
        if response.status_code >= 300:
            self.set_error()

    def add_event(self):
        if self.metadata['url'] == 'https://accounts.google.com/o/oauth2/token':
            return
        super(RequestsEvent, self).add_event()


class RequestsAuth0Event(RequestsEvent):
    """
    Represents auth0 requests event
    """

    EVENT_TYPE = 'auth0'
    API_TAG = '/api/v2/'

    def __init__(self, args):
        super(RequestsAuth0Event, self).__init__(args)
        prepared_request = args[0]
        url = prepared_request.path_url
        self.event_operation = url[url.find(self.API_TAG) + len(self.API_TAG):]


class RequestsTwilioEvent(RequestsEvent):
    """
    Represents Twilio requests event
    """

    EVENT_TYPE = 'twilio'

    def __init__(self, args):
        super(RequestsTwilioEvent, self).__init__(args)
        prepared_request = args[0]
        self.event_operation = prepared_request.path_url.split('/')[-1]


class RequestsGoogleAPIEvent(RequestsEvent):
    """
    Represents Google API requests event
    """

    EVENT_TYPE = 'googleapis'

    def __init__(self, args):
        super(RequestsGoogleAPIEvent, self).__init__(args)
        prepared_request = args[0]
        self.event_operation = '/'.join(prepared_request.path_url.split('/')[-2:])
        self.event_type = 'google_{}'.format(urlparse(prepared_request.url).path.split('/')[1])


class RequestsOutlookOfficeEvent(RequestsEvent):
    """
    Represents Outlook Office requests event
    """

    EVENT_TYPE = 'outlook.office'

    def __init__(self, args):
        super(RequestsOutlookOfficeEvent, self).__init__(args)
        prepared_request = args[0]
        self.event_operation = '/'.join(prepared_request.path_url.split('/')[-2:])


class RequestsEventFactory(object):

    @staticmethod
    def factory(args):
        factory = {
            class_obj.EVENT_TYPE: class_obj
            for class_obj in RequestsEvent.__subclasses__()
        }

        prepared_request = args[0]
        base_url = urlparse(prepared_request.url).netloc

        # Start with base event
        instance_type = RequestsEvent

        # Look for API matching in url
        for api_name in factory:
            if api_name in base_url.lower():
                instance_type = factory[api_name]

        return instance_type(args)
