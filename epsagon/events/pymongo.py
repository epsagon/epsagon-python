"""
pymongo events module
"""
from __future__ import absolute_import
from uuid import uuid4
from ..common import ErrorCode
from ..trace import tracer
from ..event import BaseEvent


class PyMongoEvent(BaseEvent):
    """
    Represents base pymongo event
    """

    EVENT_MODULE = 'pymongo'
    EVENT_TYPE = 'pymongo'

    def __init__(self, instance, args):
        super(PyMongoEvent, self).__init__()

        documents = args[0]

        self.event_id = 'pymongo-{}'.format(str(uuid4()))
        self.resource_name = instance.full_name

        self.event_operation = 'insert_many' if isinstance(documents, list) else 'insert_one'
        address = [x for x in instance.database.client._topology_settings.seeds][0]

        if self.event_operation == 'insert_one':
            documents = [documents]

        self.metadata = {
            'url': ':'.join([str(x) for x in address]),
            'db_name': str(instance.database.name),
            'collection_name': str(instance.name),
            'items': documents,
        }

    def set_error(self):
        tracer.error_code = ErrorCode.ERROR
        self.error_code = ErrorCode.ERROR

    def post_update(self, response):
        for i in xrange(len(self.metadata['items'])):
            self.metadata['items'][i]['_id'] = str(self.metadata['items'][i]['_id'])

        if self.event_operation == 'insert_many':
            self.metadata['inserted_ids'] = [str(x) for x in response.inserted_ids]
        elif self.event_operation == 'insert_one':
            self.metadata['inserted_ids'] = [str(response.inserted_id)]
