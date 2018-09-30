"""
psycopg2 patcher module
"""
from __future__ import absolute_import
import wrapt
import epsagon.modules.general_wrapper

from ..events.dbapi import DBAPIEventFactory


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

    def cursor(self, *args, **kwargs):
        """
        Return cursor wrapper.
        :param args: args.
        :param kwargs: kwargs.
        :return: Cursorwrapper.
        """
        cursor = self.__wrapped__.cursor(*args, **kwargs)
        return CursorWrapper(cursor, self)


#pylint: disable=W0613
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

#pylint: disable=W0613
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
        """
        Prepare wrapper.
        :param args:
        :param kwargs:
        :return:
        """
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
