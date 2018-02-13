"""
psycopg2 patcher module
"""
import time
import wrapt
import traceback

from ..events.dbapi import DBAPIEventFactory
from epsagon.trace import tracer
import general_wrapper


# TODO: this is a general dbapi wrapper. when we instrument another dbapi
# TODO: we should create a different module for it
class CursorWrapper(wrapt.ObjectProxy):
    """
    a dbapi cursor wrapper for tracing
    """

    def __init__(self, cursor, connection_wrapper):
        super(CursorWrapper, self).__init__(cursor)
        self._self_connection = connection_wrapper

    @property
    def connection_wrapper(self):
        return self._self_connection

    def execute(self, operation, *args, **kwargs):
        general_wrapper.wrapper(
            DBAPIEventFactory,
            self.__wrapped__.execute,
            self,
            [operation] + args,
            kwargs,
        )


# TODO: this is a general dbapi wrapper. when we instrument another dbapi
# TODO: we should create a different module for it
class ConnectionWrapper(wrapt.ObjectProxy):
    """
    a dbapi connection wrapper for tracing
    """

    def cursor(self, *args, **kwargs):
        import ipdb;ipdb.set_trace()
        cursor = self.__wrapped__.cursor(*args, **kwargs)
        return CursorWrapper(cursor)


def _connect_wrapper(wrapped, instance, args, kwargs):
    """
    connect wrapper for psycopg2 instrumentation
    :param wrapped: wrapt's wrapped
    :param instance: wrapt's instance
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    :return: None
    """

    import ipdb;ipdb.set_trace()
    connection = wrapped(*args, **kwargs)
    return ConnectionWrapper(connection)


def patch():
    """
    patch module.
    :return: None
    """

    wrapt.wrap_function_wrapper(
        'psycopg2',
        'connect',
        _connect_wrapper
    )

