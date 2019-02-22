"""
Wrapper for DB modules
"""
from __future__ import absolute_import
import wrapt
import epsagon.modules.general_wrapper
from ..events.dbapi import DBAPIEventFactory


# pylint: disable=abstract-method
class CursorWrapper(wrapt.ObjectProxy):
    """
    A dbapi cursor wrapper for tracing
    """

    def __init__(self, cursor, connection_wrapper):
        super(CursorWrapper, self).__init__(cursor)
        self._self_connection = connection_wrapper

    @property
    def connection_wrapper(self):
        """
        A property that holds that connection_wrapper.
        :return: the connection wrapper.
        """
        return self._self_connection

    # NOTE: tracing other API calls currently not supported
    # (as 'executemany' and 'callproc')
    def execute(self, *args, **kwargs):
        """
        Execute the query.
        :param args: args.
        :param kwargs: kwargs.
        """
        epsagon.modules.general_wrapper.wrapper(
            DBAPIEventFactory,
            self.__wrapped__.execute,
            self,
            args,
            kwargs,
        )

    def __enter__(self):
        # raise appropriate error if api not supported (should reach the user)
        self.__wrapped__.__enter__  # pylint: disable=W0104

        return self


class ConnectionWrapper(wrapt.ObjectProxy):
    """
    A dbapi connection wrapper for tracing.
    """
    def __init__(self, connection, args, kwargs):
        super(ConnectionWrapper, self).__init__(connection)
        self._self_args = args
        self._self_kwargs = kwargs

    def cursor(self, *args, **kwargs):
        """
        Return cursor wrapper.
        :param args: args.
        :param kwargs: kwargs.
        :return: Cursorwrapper.
        """
        cursor = self.__wrapped__.cursor(*args, **kwargs)
        return CursorWrapper(cursor, self)

    @property
    def extract_hostname(self):
        """
        A property that extract the host name
        :return: the host name
        """
        return self._self_kwargs.get('host', 'local')

    @property
    def extract_dbname(self):
        """
        A property that extract the db name
        :return: the db name
        """
        return self._self_kwargs.get(
            'db',
            self._self_kwargs.get(
                'database',
                ''
            )
        )


#pylint: disable=W0613
def connect_wrapper(wrapped, instance, args, kwargs):
    """
    connect wrapper for psycopg2 instrumentation
    :param wrapped: wrapt's wrapped
    :param instance: wrapt's instance
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    :return: None
    """
    connection = wrapped(*args, **kwargs)
    return ConnectionWrapper(connection, args, kwargs)
