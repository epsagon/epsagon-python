"""
google events module
"""
from __future__ import absolute_import
from uuid import uuid4
from ..event import BaseEvent


class GoogleRPCEvent(BaseEvent):
    """
    Represents base google rpc event
    """

    EVENT_MODULE = 'grpc'
    EVENT_TYPE = 'grpc'

    def __init__(self, wrapped, instance, args, kwargs, response, exception):
        super(GoogleRPCEvent, self).__init__()
        request_data = args[0]

        _, endpoint, operation = getattr(instance, '_method').split('/')
        endpoint = endpoint.split('.')[-1]

        self.event_id = 'grpc-{}'.format(str(uuid4()))
        self.event_operation = operation
        self.resource_name = endpoint

        self.metadata = {
            'request_data': str(request_data),
        }

        if response is not None:
            self.update_response(response)

        if exception is not None:
            self.set_error()

    def update_response(self, response):
        self.metadata['response'] = str(response)


class GRPCNaturalLanguageEvent(GoogleRPCEvent):
    """
    Represents Natural Language grpc event
    """

    EVENT_TYPE = 'LanguageService'


class GRPCEventFactory(object):
    @staticmethod
    def create_event(wrapped, instance, args, kwargs, response, exception):
        factory = {
            class_obj.EVENT_TYPE: class_obj
            for class_obj in GoogleRPCEvent.__subclasses__()
        }

        _, endpoint, _ = getattr(instance, '_method').split('/')
        endpoint = endpoint.split('.')[-1]

        try:
            event_class = factory.get(endpoint, GoogleRPCEvent)
            event = event_class(wrapped, instance, args, kwargs, response, exception)
            event.add_event()
        except Exception as ev_exception:
            print 'Epsagon Error: Could not create grpc event: {}'.format(ev_exception.message)
