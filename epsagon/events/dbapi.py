"""
sqlalchemy events module.
"""

from __future__ import absolute_import
import collections
from uuid import uuid4
import traceback

from epsagon.utils import add_data_if_needed

try:
    from psycopg2.extensions import parse_dsn

except ImportError:
    def parse_dsn(dsn):
        """
        Parse the DSN.
        :param dsn: input DSN.
        :return:
        """
        return dict(
            attribute.split("=") for attribute in dsn.split()
            if "=" in attribute
        )

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
        dsn = parse_dsn(connection.dsn)
        self.resource['name'] = dsn['dbname']
        self.resource['operation'] = self.RESOURCE_OPERATION

        # override event type with the specific DB type
        if 'rds.amazonaws' in connection.dsn:
            self.resource['type'] = 'rds'

        self.resource['metadata'] = {
            'url': dsn['host'],
            'driver': connection.__class__.__module__.split('.')[0],
            'table_name': table_name
        }

        if exception is not None:
            self.set_exception(exception, traceback.format_exc())


class DBAPIInsertEvent(DBAPIEvent):
    """
    Represents sqlalchemy insert event.
    """

    RESOURCE_OPERATION = 'insert'

    # pylint: disable=W0613
    def __init__(self, connection, cursor, args, kwargs, start_time, exception):
        """
        Initialize.
        :param connection: The SQL engine the event is using
        :param cursor: The cursor from sqlalchemy
        :param args: the arguments passed to the execution function
        :param kwargs: the arguments to the execution function
        :param start_time: Start timestamp (epoch)
        :param exception: Exception (if happened)
        """

        table_name_index = args[0].lower().split().index('into') + 1

        super(DBAPIInsertEvent, self).__init__(
            connection,
            args[0].split()[table_name_index],
            start_time,
            exception
        )

        if isinstance(args[1], (list, tuple, set)):
            items = [{
                    name: str(value) for name, value in row.iteritems()
                } if isinstance(row, collections.Mapping)
                else row  # Making sure its JSON-able
                for row in args[1]
            ]
        elif isinstance(args[1], collections.Mapping):
            items = {name: str(value) for name, value in args[1].iteritems()}
        else:
            items = [args[1]]  # Making sure its JSON-able
        add_data_if_needed(self.resource['metadata'], 'items', items)


class DBAPISelectEvent(DBAPIEvent):
    """
    Represents sqlalchemy select event.
    """

    RESOURCE_OPERATION = 'select'

    # pylint: disable=W0613
    def __init__(self, connection, cursor, args, kwargs, start_time, exception):
        """
        Initialize.
        :param connection: The SQL engine the event is using
        :param cursor: The cursor from sqlalchemy
        :param args: the arguments passed to the execution function
        :param kwargs: the arguments to the execution function
        :param start_time: Start timestamp (epoch)
        :param exception: Exception (if happened)
        """

        table_name = ' '.join(
            args[0].split()[1:])  # default anything but select keyword
        if 'from' in args[0].lower():
            table_name_index = args[0].lower().split().index('from') + 1
            table_name = args[0].split()[table_name_index]

        super(DBAPISelectEvent, self).__init__(
            connection,
            table_name,
            start_time,
            exception
        )

        if exception is None:
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
    # pylint: disable=W0613
    def create_event(wrapped, cursor_wrapper, args, kwargs, start_time,
                     response, exception):
        """
        Create an event according to the given operation.
        :param wrapped:
        :param cursor_wrapper:
        :param args:
        :param kwargs:
        :param start_time:
        :param response:
        :param exception:
        :return:
        """
        operation = args[0].split()[0].lower()
        event_class = DBAPIEventFactory.FACTORY.get(
            operation,
            None
        )

        if event_class is not None:
            event = event_class(
                cursor_wrapper.connection_wrapper,
                cursor_wrapper,
                args,
                kwargs,
                start_time,
                exception,
            )
            tracer.add_event(event)
