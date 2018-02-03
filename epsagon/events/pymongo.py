"""
pymongo events module.
"""

from __future__ import absolute_import
from uuid import uuid4
import traceback
from ..event import BaseEvent
from ..trace import tracer


class PyMongoEvent(BaseEvent):
    """
    Represents base pymongo event.
    """

    ORIGIN = 'pymongo'
    RESOURCE_TYPE = 'pymongo'

    def __init__(self, wrapped, instance, args, kwargs, start_time, response, exception):
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

        documents = args[0]

        self.event_id = 'mongo-{}'.format(str(uuid4()))
        self.resource['name'] = instance.full_name

        self.resource['operation'] = 'insert_many' if isinstance(documents, list) else 'insert_one'
        address = [x for x in getattr(instance.database.client, '_topology_settings').seeds][0]

        if self.resource['operation'] == 'insert_one':
            documents = [documents]

        self.resource['metadata'] = {
            'url': ':'.join([str(x) for x in address]),
            'db_name': str(instance.database.name),
            'collection_name': str(instance.name),
            'items': documents,
        }

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

        for i in xrange(len(self.resource['metadata']['items'])):
            self.resource['metadata']['items'][i]['_id'] = str(
                self.resource['metadata']['items'][i]['_id']
            )

        if self.resource['operation'] == 'insert_many':
            self.resource['metadata']['inserted_ids'] = [str(x) for x in response.inserted_ids]
        elif self.resource['operation'] == 'insert_one':
            self.resource['metadata']['inserted_ids'] = [str(response.inserted_id)]


class PyMongoEventFactory(object):
    """
    Factory class, generates MongoDB event.
    """

    @staticmethod
    def create_event(wrapped, instance, args, kwargs, start_time, response, exception):
        event = PyMongoEvent(wrapped, instance, args, kwargs, start_time, response, exception)
        tracer.add_event(event)
