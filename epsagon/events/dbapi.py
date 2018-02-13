"""
sqlalchemy events module.
"""

from __future__ import absolute_import
from uuid import uuid4
import sys
import traceback
from ..trace import tracer
from ..event import BaseEvent


class DBAPIEvent(BaseEvent):
    """
    Represents base sqlalchemy event.
    """

    ORIGIN = 'dbapi'
    RESOURCE_TYPE = 'database'
    RESOURCE_OPERATION = None

    def __init__(self, connection, table_name, start_time, exception):
        """
        Initialize.
        :param connection: The SQL engine the event is using
        :param table_name: the table the event is occurring on
        :param start_time: Start timestamp (epoch)
        :param exception: Exception (if occurred)
        """

        super(DBAPIEvent, self).__init__(start_time)

        self.event_id = 'dbapi-{}'.format(str(uuid4()))
        self.resource['name'] = connection.url.database
        self.resource['operation'] = self.RESOURCE_OPERATION

        # override event type with the specific DB type
        if 'rds.amazonaws' in repr(connection.url):
            self.resource['type'] = 'rds'

        self.resource['metadata'] = {
            'url': repr(connection.url),
            'driver': connection.url.drivername,
            'table_name': table_name
        }

        if exception is not None:
            self.set_exception(exception, traceback.format_exc())


class DBAPIInsertEvent(DBAPIEvent):
    """
    Represents sqlalchemy insert event.
    """

    RESOURCE_OPERATION = 'insert'

    def __init__(self, connection, cursor, operation, kwargs, start_time, exception):
        """
        Initialize.
        :param connection: The SQL engine the event is using
        :param cursor: The cursor from sqlalchemy
        :param operation: the SQL statement that was executed
        :param kwargs: the arguments to the sql statement
        :param start_time: Start timestamp (epoch)
        :param exception: Exception (if happened)
        """

        table_name_index = operation.lower().split().index('into') + 1

        super(DBAPIInsertEvent, self).__init__(
            connection,
            operation.split()[table_name_index],
            start_time,
            exception
        )

        self.resource['metadata']['items'] = [{
                name: str(value) for name, value in arg.iteritems()
            } for arg in kwargs[0]
        ]


class DBAPISelectEvent(DBAPIEvent):
    """
    Represents sqlalchemy select event.
    """

    RESOURCE_OPERATION = 'select'

    def __init__(self, connection, cursor, operation, kwargs, start_time, exception):
        """
        Initialize.
        :param connection: The SQL engine the event is using
        :param cursor: The cursor from sqlalchemy
        :param operation: the SQL statement that was executed
        :param kwargs: the arguments to the sql statement
        :param start_time: Start timestamp (epoch)
        :param exception: Exception (if happened)
        """

        table_name_index = operation.lower().split().index('from') + 1

        super(DBAPISelectEvent, self).__init__(
            connection,
            operation.split()[table_name_index],
            start_time,
            exception
        )

        if exception is not None:
            self.update_response(cursor)

    def update_response(self, cursor):
        """
        Adds response data to event.
        :param cursor: The cursor to the response
        :return: None
        """

        self.resource['metadata']['items_count'] = int(cursor.rowcount)


class DBAPIEventFactory(object):
    """
    Factory class, generates dbapi event.
    """

    FACTORY = {
        class_obj.RESOURCE_OPERATION: class_obj
        for class_obj in DBAPIEvent.__subclasses__()
    }

    @staticmethod
    def create_event(wrapped, cursor_wrapper, args, kwargs, start_time, response, exception):
        import ipdb;ipdb.set_trace()
        operation = args[0].split()[0].lower()
        event_class = DBAPIEventFactory.FACTORY.get(
            operation,
            None
        )

        if event_class is not None:
            event = event_class(
                cursor_wrapper.connection_wrapper,
                cursor_wrapper,
                operation,
                kwargs,
                start_time,
                exception,
            )
            tracer.add_event(event)
    # def create_event(connection, cursor, operation, kwargs, start_time):
    #     operation = operation.split()[0].lower()
    #     event_class = DBAPIEventFactory.FACTORY.get(
    #         operation,
    #         None
    #     )
    #
    #     if event_class is not None:
    #         event = event_class(
    #             connection,
    #             cursor,
    #             operation,
    #             kwargs,
    #             start_time,
    #             sys.exc_info()[0]
    #         )
    #         tracer.add_event(event)
