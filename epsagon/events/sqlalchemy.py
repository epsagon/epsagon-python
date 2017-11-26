"""
sqlalchemy events module
"""
from __future__ import absolute_import
from urlparse import urlparse
from uuid import uuid4
from ..common import ErrorCode
from ..trace import tracer
from ..event import BaseEvent


class SQLAlchemyEvent(BaseEvent):
    """
    Represents base sqlalchemy event
    """

    EVENT_MODULE = 'sqlalchemy'
    EVENT_TYPE = 'sqlalchemy'
    EVENT_OPERATION = None

    def __init__(self, instance, args):
        super(SQLAlchemyEvent, self).__init__()

        self.event_id = 'sqlalchemy-{}'.format(str(uuid4()))
        self.resource_name = instance.bind.url.database
        self.event_operation = self.EVENT_OPERATION

        # override event type with the specific DB type
        if 'rds.amazonaws' in repr(instance.bind.url):
            self.event_type = 'rds'

        self.metadata = {
            'url': repr(instance.bind.url),
            'driver': instance.bind.url.drivername,
        }

    def set_error(self):
        tracer.error_code = ErrorCode.ERROR
        self.error_code = ErrorCode.ERROR

    def post_update(self, response):
        pass


class SQLAlchemyCommitEvent(SQLAlchemyEvent):
    """
    Represents sqlalchemy commit event
    """

    EVENT_OPERATION = 'add'

    def __init__(self, instance, args):
        super(SQLAlchemyCommitEvent, self).__init__(instance, args)

        # Currently support only add
        items = [{'object': str(x), 'table': x.__tablename__} for x in instance._new.values()]

        self.metadata['items'] = items


class SQLAlchemyQueryEvent(SQLAlchemyEvent):
    """
    Represents sqlalchemy query event
    """

    EVENT_OPERATION = 'query'

    def __init__(self, instance, args):
        super(SQLAlchemyQueryEvent, self).__init__(instance, args)
        query_element = args[0]
        self.metadata['table_name'] = query_element.__tablename__

    def post_update(self, response):
        self.metadata['items_count'] = int(response.count())


class SQLAlchemyEventFactory(object):

    @staticmethod
    def factory(wrapped, instance, args):
        factory = {
            class_obj.EVENT_OPERATION: class_obj
            for class_obj in SQLAlchemyEvent.__subclasses__()
        }

        return factory.get(wrapped.im_func.func_name, SQLAlchemyEvent)(instance, args)
