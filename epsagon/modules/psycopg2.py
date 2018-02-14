"""
psycopg2 patcher module
"""
import wrapt

from ..events.dbapi import DBAPIEventFactory
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

    #TODO: handle arguments name correctly. might not be query in different libraries
    def execute(self, query, *args, **kwargs):
        general_wrapper.wrapper(
            DBAPIEventFactory,
            self.__wrapped__.execute,
            self,
            (query, ) + args,
            kwargs,
        )

    #TODO: handle arguments name correctly. might not be query in different libraries
    def executemany(self, query, *args, **kwargs):
        general_wrapper.wrapper(
            DBAPIEventFactory,
            self.__wrapped__.executemany,
            self,
            (query, ) + args,
            kwargs,
        )

    #TODO: handle arguments name correctly. might not be query in different libraries
    def callproc(self, proc, args):
        general_wrapper.wrapper(
            DBAPIEventFactory,
            self.__wrapped__.callproc,
            self,
            [proc, args],
            {}
        )

    def __enter__(self):
        # raise appropriate error if api not supported (should reach the user)
        self.__wrapped__.__enter__

        return self


# TODO: this is a general dbapi wrapper. when we instrument another dbapi
# TODO: we should create a different module for it
class ConnectionWrapper(wrapt.ObjectProxy):
    """
    a dbapi connection wrapper for tracing
    """

    def cursor(self, *args, **kwargs):
        cursor = self.__wrapped__.cursor(*args, **kwargs)
        return CursorWrapper(cursor, self)


def _connect_wrapper(wrapped, instance, args, kwargs):
    """
    connect wrapper for psycopg2 instrumentation
    :param wrapped: wrapt's wrapped
    :param instance: wrapt's instance
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    :return: None
    """

    connection = wrapped(*args, **kwargs)
    return ConnectionWrapper(connection)


def _register_type_wrapper(wrapped, instance, args, kwargs):
    """
    register_type wrapper for psycopg2 instrumentation
    :param wrapped: wrapt's wrapped
    :param instance: wrapt's instance
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    :return: None
    """

    def _extract_arguments(obj, scope=None):
        return obj, scope

    obj, scope = _extract_arguments(*args, **kwargs)

    if scope is not None:
        if isinstance(scope, wrapt.ObjectProxy):
            scope = scope.__wrapped__
        return wrapped(obj, scope)

    return wrapped(obj)


class AdapterWrapper(wrapt.ObjectProxy):
    """
    a wrapper for an adapter, to strip the connection out of the objectProxy
    before calling prepare
    """

    def prepare(self, *args, **kwargs):
        if not args:
            return self.__wrapped__.prepare(*args, **kwargs)

        connection = args[0]
        if isinstance(connection, wrapt.ObjectProxy):
            connection = connection.__wrapped__

        return self.__wrapped__.prepare(connection, *args[1:], **kwargs)


def _adapt_wrapper(wrapped, instance, args, kwargs):
    """
    adapt wrapper for psycopg2 instrumentation
    :param wrapped: wrapt's wrapped
    :param instance: wrapt's instance
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    :return: None
    """

    adapter = wrapped(*args, **kwargs)
    return AdapterWrapper(adapter) if hasattr(adapter, 'prepare') else adapter


def _patch_unwrappers():
    """
    patches the functions that do not accept our ObjectProxy to strip the proxy
    before calling the function
    :return:
    """

    wrapt.wrap_function_wrapper(
        'psycopg2.extensions',
        'register_type',
        _register_type_wrapper
    )

    wrapt.wrap_function_wrapper(
        'psycopg2._psycopg',
        'register_type',
        _register_type_wrapper
    )

    wrapt.wrap_function_wrapper(
        'psycopg2._json',
        'register_type',
        _register_type_wrapper
    )

    wrapt.wrap_function_wrapper(
        'psycopg2.extensions',
        'adapt',
        _adapt_wrapper
    )


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
    _patch_unwrappers()

