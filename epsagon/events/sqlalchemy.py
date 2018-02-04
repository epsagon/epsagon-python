"""
sqlalchemy events module.
"""

from __future__ import absolute_import
from uuid import uuid4
import traceback
from ..trace import tracer
from ..event import BaseEvent


class SQLAlchemyEvent(BaseEvent):
    """
    Represents base sqlalchemy event.
    """

    ORIGIN = 'sqlalchemy'
    RESOURCE_TYPE = 'sqlalchemy'
    RESOURCE_OPERATION = None

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

        super(SQLAlchemyEvent, self).__init__(start_time)

        self.event_id = 'sqlalchemy-{}'.format(str(uuid4()))
        self.resource['name'] = instance.bind.url.database
        self.resource['operation'] = self.RESOURCE_OPERATION

        # override event type with the specific DB type
        if 'rds.amazonaws' in repr(instance.bind.url):
            self.resource['type'] = 'rds'

        self.resource['metadata'] = {
            'url': repr(instance.bind.url),
            'driver': instance.bind.url.drivername,
        }

        if exception is not None:
            self.set_exception(exception, traceback.format_exc())


class SQLAlchemyCommitEvent(SQLAlchemyEvent):
    """
    Represents sqlalchemy commit event.
    """

    RESOURCE_OPERATION = 'add'

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

        super(SQLAlchemyCommitEvent, self).__init__(
            wrapped,
            instance,
            args,
            kwargs,
            start_time,
            response,
            exception
        )

        # Currently support only add
        items = [
            {'object': str(x), 'table': x.__tablename__} for x in
            getattr(instance, '_new').values()
        ]

        self.resource['metadata']['items'] = items


class SQLAlchemyQueryEvent(SQLAlchemyEvent):
    """
    Represents sqlalchemy query event.
    """

    RESOURCE_OPERATION = 'query'

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

        super(SQLAlchemyQueryEvent, self).__init__(
            wrapped,
            instance,
            args,
            kwargs,
            start_time,
            response,
            exception
        )

        query_element = args[0]
        self.resource['metadata']['table_name'] = query_element.__tablename__

        if response is not None:
            self.update_response(response)

    def update_response(self, response):
        """
        Adds response data to event.
        :param response: Response from botocore
        :return: None
        """

        self.resource['metadata']['items_count'] = int(response.count())


class SQLAlchemyEventFactory(object):
    """
    Factory class, generates SQL alchemy event.
    """

    FACTORY = {
        class_obj.RESOURCE_OPERATION: class_obj
        for class_obj in SQLAlchemyEvent.__subclasses__()
    }

    @staticmethod
    def create_event(wrapped, instance, args, kwargs, start_time, response,
                     exception):
        event_class = SQLAlchemyEventFactory.FACTORY.get(
            wrapped.im_func.func_name,
            SQLAlchemyEvent
        )
        event = event_class(
            wrapped,
            instance,
            args,
            kwargs,
            start_time,
            response,
            exception
        )
        tracer.add_event(event)
