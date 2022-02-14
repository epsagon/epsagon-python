"""
pymongo events module.
"""

from __future__ import absolute_import
from uuid import uuid4
import traceback

from epsagon.utils import add_data_if_needed
from ..event import BaseEvent
from ..trace import trace_factory


class PyMongoEvent(BaseEvent):
    """
    Represents base pymongo event.
    """

    ORIGIN = 'pymongo'
    RESOURCE_TYPE = 'pymongo'
    INSERT_ONE = 'insert_one'
    INSERT_MANY = 'insert_many'
    INSERT_OPERATIONS = (INSERT_ONE, INSERT_MANY)
    FILTER_OPERATIONS = ('find', 'update_one', 'delete_many')

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
        super(PyMongoEvent, self).__init__(start_time)

        self.resource['operation'] = getattr(wrapped, '__name__')

        self.event_id = 'mongo-{}'.format(str(uuid4()))
        self.resource['name'] = instance.name
        address = list(getattr(
            instance.database.client,
            '_topology_settings'
            ).seeds)[0]

        self.resource['metadata'] = {
                'DB URL': ':'.join([str(x) for x in address]),
                'DB Name': str(instance.database.name),
                'Collection Name': str(instance.collection.name),
            }

        if args:
            self.handle_request_payload(args)

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

        if self.resource['operation'] in PyMongoEvent.INSERT_OPERATIONS:
            self.handle_insert_operations_response(response)

        elif self.resource['operation'] in PyMongoEvent.FILTER_OPERATIONS:
            self.handle_filter_operations_response(response)


    def handle_request_payload(self, input_args):
        """
        Handle input data before add to event.
        :param input_args: input from botocore
        :return: None
        """

        if self.resource['operation'] == PyMongoEvent.INSERT_MANY:
            add_data_if_needed(self.resource['metadata'], 'Items',
                input_args[0])

        elif self.resource['operation'] == PyMongoEvent.INSERT_ONE:
            add_data_if_needed(self.resource['metadata'], 'Item',
                input_args[0])

        elif self.resource['operation'] in PyMongoEvent.FILTER_OPERATIONS:
            add_data_if_needed(self.resource['metadata'], 'Filter',
                input_args[0])

            if self.resource['operation'] == 'update_one':
                add_data_if_needed(self.resource['metadata'], 'New Values',
                    input_args[1])


    def handle_insert_operations_response(self, response):
        """
        Handle response data before add to event.
        :param response: response from botocore
        :return: None
        """

        if self.resource['operation'] == PyMongoEvent.INSERT_MANY:
            self.resource['metadata']['inserted_ids'] = \
                    [str(x) for x in response.inserted_ids]

        elif self.resource['operation'] == PyMongoEvent.INSERT_ONE:
            self.resource['metadata']['inserted_id'] = \
                    [str(response.inserted_id)]


    def handle_filter_operations_response(self, response):
        """
        Handle response data before add to event.
        :param response: response from botocore
        :return: None
        """

        if self.resource['operation'] == 'find':
            self.resource['metadata']['Results'] = \
                        [response[i] for i in range(response.count())]

        elif self.resource['operation'] == 'update_one':
            self.resource['metadata']['matched_count'] = \
                        response.matched_count
            self.resource['metadata']['modified_count'] = \
                        response.modified_count

        elif self.resource['operation'] == 'delete_many':
            self.resource['metadata']['deleted_count'] = \
                        response.deleted_count


class PyMongoEventFactory(object):
    """
    Factory class, generates MongoDB event.
    """

    @staticmethod
    def create_event(wrapped, instance, args, kwargs, start_time, response,
                     exception):
        """
        Create a PyMongo event.
        :param wrapped:
        :param instance:
        :param args:
        :param kwargs:
        :param start_time:
        :param response:
        :param exception:
        :return:
        """
        event = PyMongoEvent(
            wrapped,
            instance,
            args,
            kwargs,
            start_time,
            response,
            exception
        )
        trace_factory.add_event(event)
