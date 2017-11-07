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

    def __init__(self, instance, args):
        super(GoogleRPCEvent, self).__init__()
        request_data = args[0]

        _, endpoint, operation = instance._method.split('/')
        endpoint = endpoint.split('.')[-1]

        self.event_id = 'g{}'.format(str(uuid4()))
        self.event_operation = operation
        self.resource_name = endpoint

        print type(request_data), dir(request_data)
        self.metadata = {
            'request_data': str(request_data),
        }

    def post_update(self, parsed_response):
        self.metadata['response'] = str(parsed_response)


class GRPCNaturalLanguageEvent(GoogleRPCEvent):
    """
    Represents Natural Language grpc event
    """

    EVENT_TYPE = 'LanguageService'


class GRPCEventFactory(object):

    @staticmethod
    def factory(instance, args):
        factory = {
            class_obj.EVENT_TYPE: class_obj
            for class_obj in GoogleRPCEvent.__subclasses__()
        }

        _, endpoint, _ = getattr(instance, '_method').split('/')
        endpoint = endpoint.split('.')[-1]

        return factory.get(endpoint, GoogleRPCEvent)(instance, args)
