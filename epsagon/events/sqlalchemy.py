"""
sqlalchemy events module.
"""

from __future__ import absolute_import
from uuid import uuid4
import sys
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

    def __init__(self, engine, table_name, start_time, exception):
        """
        Initialize.
        :param engine: The SQL engine the event is using
        :param table_name: the table the event is occurring on
        :param start_time: Start timestamp (epoch)
        :param exception: Exception (if occurred)
        """

        super(SQLAlchemyEvent, self).__init__(start_time)

        self.event_id = 'sqlalchemy-{}'.format(str(uuid4()))
        self.resource['name'] = engine.url.database
        self.resource['operation'] = self.RESOURCE_OPERATION

        # override event type with the specific DB type
        if 'rds.amazonaws' in repr(engine.url):
            self.resource['type'] = 'rds'

        self.resource['metadata'] = {
            'url': repr(engine.url),
            'driver': engine.url.drivername,
            'table_name': table_name
        }

        if exception is not None:
            self.set_exception(exception, traceback.format_exc())


class SQLAlchemyInsertEvent(SQLAlchemyEvent):
    """
    Represents sqlalchemy insert event.
    """

    RESOURCE_OPERATION = 'insert'

    def __init__(self, engine, cursor, statement, args,  start_time, exception):
        """
        Initialize.
        :param engine: The SQL engine the event is using
        :param cursor: The cursor from sqlalchemy
        :param statement: the SQL statement that was executed
        :param args: the arguments to the sql statement
        :param start_time: Start timestamp (epoch)
        :param exception: Exception (if happened)
        """

        table_name_index = statement.lower().split().index('into') + 1

        super(SQLAlchemyInsertEvent, self).__init__(
            engine,
            statement.split()[table_name_index],
            start_time,
            exception
        )

        self.resource['metadata']['items'] = [{
                name: str(value) for name, value in arg.iteritems()
            } for arg in args[0]
        ]


class SQLAlchemySelectEvent(SQLAlchemyEvent):
    """
    Represents sqlalchemy select event.
    """

    RESOURCE_OPERATION = 'select'

    def __init__(self, engine, cursor, statement, args,  start_time, exception):
        """
        Initialize.
        :param engine: The SQL engine the event is using
        :param cursor: The cursor from sqlalchemy
        :param statement: the SQL statement that was executed
        :param args: the arguments to the sql statement
        :param start_time: Start timestamp (epoch)
        :param exception: Exception (if happened)
        """

        table_name_index = statement.lower().split().index('from') + 1

        super(SQLAlchemySelectEvent, self).__init__(
            engine,
            statement.split()[table_name_index],
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


class SQLAlchemyEventFactory(object):
    """
    Factory class, generates SQL alchemy event.
    """

    FACTORY = {
        class_obj.RESOURCE_OPERATION: class_obj
        for class_obj in SQLAlchemyEvent.__subclasses__()
    }

    @staticmethod
    def create_event(engine, cursor, statement, args, start_time):
        operation = statement.split()[0].lower()
        event_class = SQLAlchemyEventFactory.FACTORY.get(
            operation,
            None
        )

        if event_class is not None:
            event = event_class(
                engine,
                cursor,
                statement,
                args,
                start_time,
                sys.exc_info()[0]
            )
            tracer.add_event(event)
