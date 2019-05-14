"""
google events module.
"""

from __future__ import absolute_import
from uuid import uuid4
import traceback

from epsagon.utils import add_data_if_needed
from ..event import BaseEvent
from ..trace import trace_factory


class GoogleRPCEvent(BaseEvent):
    """
    Represents base google rpc event
    """

    ORIGIN = 'grpc'
    RESOURCE_TYPE = 'grpc'

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

        super(GoogleRPCEvent, self).__init__(start_time)

        request_data = args[0]

        _, endpoint, operation = getattr(instance, '_method').split('/')
        endpoint = endpoint.split('.')[-1]

        self.event_id = 'grpc-{}'.format(str(uuid4()))
        self.resource['operation'] = operation
        self.resource['name'] = endpoint

        add_data_if_needed(
            self.resource['metadata'],
            'Request Data',
            str(request_data)
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

        add_data_if_needed(
            self.resource['metadata'],
            'Response Data',
            str(response)
        )


class GRPCNaturalLanguageEvent(GoogleRPCEvent):
    """
    Represents Natural Language grpc event.
    """

    RESOURCE_TYPE = 'LanguageService'


class GRPCEventFactory(object):
    """
    Factory class, generates google rpc event.
    """

    FACTORY = {
        class_obj.RESOURCE_TYPE: class_obj
        for class_obj in GoogleRPCEvent.__subclasses__()
    }

    @staticmethod
    def create_event(wrapped, instance, args, kwargs, start_time, response,
                     exception):
        """
        Create an event according to the given endpoint.
        :param wrapped:
        :param instance:
        :param args:
        :param kwargs:
        :param start_time:
        :param response:
        :param exception:
        :return:
        """
        _, endpoint, _ = getattr(instance, '_method').split('/')
        endpoint = endpoint.split('.')[-1]

        event_class = GRPCEventFactory.FACTORY.get(endpoint, GoogleRPCEvent)
        event = event_class(
            wrapped,
            instance,
            args,
            kwargs,
            start_time,
            response,
            exception
        )
        trace_factory.add_event(event)
