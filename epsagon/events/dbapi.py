"""
sqlalchemy events module.
"""

from __future__ import absolute_import
from uuid import uuid4
import traceback

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
            attribute.split('=') for attribute in dsn.split()
            if '=' in attribute
        )

from ..trace import tracer
from ..event import BaseEvent

MAX_QUERY_SIZE = 2048


class DBAPIEvent(BaseEvent):
    """
    Represents base sqlalchemy event.
    """

    ORIGIN = 'dbapi'
    RESOURCE_TYPE = 'database'
    RESOURCE_OPERATION = None

    # mapping SQL commands to words preceding the table name in the query
    # Note: Not supporting advanced syntax of select and delete (as 'delete
    # from only ..')
    _OPERATION_TO_TABLE_NAME_KEYWORD = {
        'select': 'from',
        'insert': 'into',
        'update': 'update',
        'delete': 'from',
        'create': 'table'
    }

    def __init__(
            self,
            connection,
            cursor,
            _args,
            _kwargs,
            start_time,
            exception
    ):
        """
        Initialize.
        :param connection: The SQL engine the event is using
        :param cursor: Cursor object used in the even
        :param args: args passed to called function
        :param kwargs: kwargs passed to called function
        :param start_time: Start timestamp (epoch)
        :param exception: Exception (if occurred)
        """

        super(DBAPIEvent, self).__init__(start_time)

        self.event_id = 'dbapi-{}'.format(str(uuid4()))

        # in case of pg instrumentation we extract data from the dsn property
        if hasattr(connection, 'dsn'):
            dsn = parse_dsn(connection.dsn)
            db_name = dsn['dbname']
            host = dsn.get('host', 'local')
            query = cursor.query
        else:
            query = _args[0]
            host = connection.extract_hostname
            db_name = connection.extract_dbname

        self.resource['name'] = db_name

        # NOTE: The operation might not be identified properly when
        # using 'WITH' clause
        operation = query.split()[0].lower()
        self.resource['operation'] = operation

        # override event type with the specific DB type
        if 'rds.amazonaws' in host:
            self.resource['type'] = 'rds'
        elif 'redshift.amazonaws' in host:
            self.resource['type'] = 'redshift'

        self.resource['metadata'] = {
            'Host': host,
            'Driver': connection.__class__.__module__.split('.')[0],
            'Table Name': self._extract_table_name(query, operation)
        }

        # for select we always want to save the query
        if (operation == 'select') or (not tracer.metadata_only):
            self.resource['metadata']['Query'] = query[:MAX_QUERY_SIZE]

        if exception is None:
            # Update response data
            self.resource['metadata']['Related Rows Count'] = int(
                cursor.rowcount
            )
        else:
            self.set_exception(exception, traceback.format_exc())

    @staticmethod
    def _extract_table_name(query, operation):
        """
        Extract the table name from the SQL query string
        :param query: The SQL query string
        :param operation: The SQL operation used in the query
            (SELECT, INSERT, etc.)
        :return: Table name (string), "" if couldn't find
        """

        if operation in DBAPIEvent._OPERATION_TO_TABLE_NAME_KEYWORD:
            keyword = DBAPIEvent._OPERATION_TO_TABLE_NAME_KEYWORD[operation]
            query_words = query.lower().split()
            if keyword in query_words:
                return query.split()[query_words.index(keyword) + 1]

        return ''


class DBAPIEventFactory(object):
    """
    Factory class, generates dbapi event.
    """

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
        event = DBAPIEvent(
            cursor_wrapper.connection_wrapper,
            cursor_wrapper,
            args,
            kwargs,
            start_time,
            exception,
        )
        tracer.add_event(event)
