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

        self.metadata = {
            'request_data': request_data,
        }

    def post_update(self, parsed_response):
        self.metadata['response'] = str(parsed_response)


class GRPCNaturalLanguageEvent(GoogleRPCEvent):
    """
    Represents Natural Language grpc event
    """

    EVENT_TYPE = 'LanguageService'


class GRPCEventFactory(object):

    FACTORY_DICT = {
        GRPCNaturalLanguageEvent.EVENT_TYPE: GRPCNaturalLanguageEvent,
    }

    @staticmethod
    def factory(instance, args):
        _, endpoint, _ = getattr(instance, '_method').split('/')
        endpoint = endpoint.split('.')[-1]

        return GRPCEventFactory.FACTORY_DICT.get(endpoint, GoogleRPCEvent)(instance, args)
