"""
pymongo events module.
"""

from __future__ import absolute_import
from uuid import uuid4
import traceback
from past.builtins import range

from epsagon.utils import add_data_if_needed
from ..event import BaseEvent
from ..trace import trace_factory


class PyMongoEvent(BaseEvent):
    """
    Represents base pymongo event.
    """

    ORIGIN = 'pymongo'
    RESOURCE_TYPE = 'pymongo'
    INSERT_OPERATIONS = ['insert_one', 'insert_many']
    FILTER_OPERATIONS = ['find', 'update_one', 'delete_many']

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

        if len(args) == 0:
            documents = list()

        else:
            documents = args[0]

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

        if self.resource['operation'] in PyMongoEvent.INSERT_OPERATIONS:
            add_data_if_needed(self.resource['metadata'], 'Items', documents)
        
        elif self.resource['operation'] in PyMongoEvent.FILTER_OPERATIONS:
            add_data_if_needed(self.resource['metadata'], 'Search', documents)

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
            for i in range(len(self.resource['metadata'].get('items', []))):
                self.resource['metadata']['items'][i]['_id'] = str(
                    self.resource['metadata']['items'][i]['_id']
                )

            if self.resource['operation'] == 'insert_many':
                self.resource['metadata']['inserted_ids'] = \
                    [str(x) for x in response.inserted_ids]
            elif self.resource['operation'] == 'insert_one':
                self.resource['metadata']['inserted_ids'] = \
                    [str(response.inserted_id)]

        elif self.resource['operation'] in PyMongoEvent.FILTER_OPERATIONS:
            self.resource['metadata']['Search'] = str(
                    self.resource['metadata']['Search']
                )
            
            if self.resource['operation'] == 'find':
                self.resource['metadata']['Results'] = \
                        [x for x in response]
        
            elif self.resource['operation'] in ['update_one']:
                self.resource['metadata']['matched_count'] = \
                        response.matched_count
                self.resource['metadata']['modified_count'] = \
                        response.modified_count
        
            elif self.resource['operation'] in ['delete_many']:  
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
