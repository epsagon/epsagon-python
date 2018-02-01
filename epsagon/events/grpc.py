"""
google events module
"""
from __future__ import absolute_import
from uuid import uuid4
from ..event import BaseEvent
from ..trace import tracer

class GoogleRPCEvent(BaseEvent):
    """
    Represents base google rpc event
    """

    EVENT_MODULE = 'grpc'
    RESOURCE_TYPE = 'grpc'

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

    RESOURCE_TYPE = 'LanguageService'


class GRPCEventFactory(object):
    FACTORY = {
        class_obj.RESOURCE_TYPE: class_obj
        for class_obj in GoogleRPCEvent.__subclasses__()
    }
    @staticmethod
    def create_event(wrapped, instance, args, kwargs, response, exception):

        _, endpoint, _ = getattr(instance, '_method').split('/')
        endpoint = endpoint.split('.')[-1]

        event_class = GRPCEventFactory.FACTORY.get(endpoint, GoogleRPCEvent)
        event = event_class(wrapped, instance, args, kwargs, response, exception)
        tracer.add_event(event)
