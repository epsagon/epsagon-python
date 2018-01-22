"""
sqlalchemy events module
"""
from __future__ import absolute_import
from uuid import uuid4
from ..event import BaseEvent


class SQLAlchemyEvent(BaseEvent):
    """
    Represents base sqlalchemy event
    """

    EVENT_MODULE = 'sqlalchemy'
    EVENT_TYPE = 'sqlalchemy'
    EVENT_OPERATION = None

    def __init__(self, wrapped, instance, args, kwargs, response, exception):
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

        if response is not None:
            self.update_response(response)

        if exception is not None:
            self.set_error()


class SQLAlchemyCommitEvent(SQLAlchemyEvent):
    """
    Represents sqlalchemy commit event
    """

    EVENT_OPERATION = 'add'

    def __init__(self, wrapped, instance, args, kwargs, response, exception):
        super(SQLAlchemyCommitEvent, self).__init__(wrapped, instance, args, kwargs, response,
                                                    exception)

        # Currently support only add
        items = [{'object': str(x), 'table': x.__tablename__}
                 for x in getattr(instance, '_new').values()]

        self.metadata['items'] = items


class SQLAlchemyQueryEvent(SQLAlchemyEvent):
    """
    Represents sqlalchemy query event
    """

    EVENT_OPERATION = 'query'

    def __init__(self, wrapped, instance, args, kwargs, response, exception):
        super(SQLAlchemyQueryEvent, self).__init__(wrapped, instance, args, kwargs, response,
                                                   exception)

        query_element = args[0]
        self.metadata['table_name'] = query_element.__tablename__

    def update_response(self, response):
        self.metadata['items_count'] = int(response.count())


class SQLAlchemyEventFactory(object):
    @staticmethod
    def create_event(wrapped, instance, args, kwargs, response, exception):
        factory = {
            class_obj.EVENT_OPERATION: class_obj
            for class_obj in SQLAlchemyEvent.__subclasses__()
        }

        event_class = factory.get(wrapped.im_func.func_name, SQLAlchemyEvent)
        event = event_class(wrapped, instance, args, kwargs, response, exception)
        event.add_event()
