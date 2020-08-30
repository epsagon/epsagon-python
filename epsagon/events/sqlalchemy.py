"""
sqlalchemy events module.
"""

from __future__ import absolute_import
import traceback
from uuid import uuid4

from ..trace import trace_factory
from ..event import BaseEvent
from ..utils import database_connection_type


class SqlAlchemyEvent(BaseEvent):
    """
    Represents base SqlAlchemy event.
    """

    ORIGIN = 'sqlalchemy'
    RESOURCE_TYPE = 'database'

    # pylint: disable=W0613
    def __init__(self, wrapped, instance, args, kwargs, start_time, response,
                 exception, operation):
        """
        Initialize.
        :param wrapped: wrapt's wrapped
        :param instance: wrapt's instance
        :param args: wrapt's args
        :param kwargs: wrapt's kwargs
        :param start_time: Start timestamp (epoch)
        :param response: response data
        :param exception: Exception (if happened)
        :param operation: sqlalchemy operation
        """
        super(SqlAlchemyEvent, self).__init__(start_time)

        self.event_id = 'sqlalchemy-{}'.format(str(uuid4()))

        self.resource['name'] = (
                instance.bind.url.database or instance.bind.url.host
        )
        self.resource['operation'] = operation

        # override event type with the specific DB type
        self.resource['type'] = database_connection_type(
            instance.bind.url.host,
            self.RESOURCE_TYPE
        )

        if exception is not None:
            self.set_exception(exception, traceback.format_exc())


class SqlAlchemyEventFactory(object):
    """
    Factory class, generates sqlalchemy event.
    """

    OPERATION_MAPPING = {
        '__init__': 'initialize',
        'close': 'close',
    }

    @staticmethod
    def create_event(wrapped, instance, args, kwargs, start_time, response,
                     exception):
        """
        Create sqlalchemy initialize/close event.
        """
        operation = SqlAlchemyEventFactory.OPERATION_MAPPING.get(
            getattr(wrapped, '__name__')
        )

        if not operation:
            return

        event = SqlAlchemyEvent(
            wrapped,
            instance,
            args,
            kwargs,
            start_time,
            response,
            exception,
            operation
        )

        trace_factory.add_event(event)
