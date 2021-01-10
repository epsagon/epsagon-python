"""
redis events module.
"""

from __future__ import absolute_import
from uuid import uuid4
import traceback

from ..event import BaseEvent
from ..trace import trace_factory
from ..utils import add_data_if_needed


MAX_VALUE_SIZE = 1024
MAX_CMD_PIPELINE = 10


def _parse_redis_cmd(cmd_args):
    """
    Parse redis cmd to operation, arguments
    :param cmd_args: command arguments
    :return: operation, key
    """
    key = ''
    operation = str(cmd_args[0])[:MAX_VALUE_SIZE]
    if len(cmd_args) > 1:
        key = str(cmd_args[1])[:MAX_VALUE_SIZE]
    return operation, key


def _parse_redis_connection(connection):
    """
    Parse redis connection to host, db
    :param connection: redis connection
    :return: host, db
    """
    connection_kwargs = connection.connection_pool.connection_kwargs
    return (
        connection_kwargs.get('host', 'local'),
        connection_kwargs.get('port'),
        connection_kwargs.get('db', '0')
    )


class BaseRedisEvent(BaseEvent):
    """
    Represents base redis event.
    """
    ORIGIN = 'redis'
    RESOURCE_TYPE = 'redis'

    # pylint: disable=W0613
    def __init__(self, wrapped, instance, args, kwargs, start_time, response,
                 exception):
        """
        Initialize the redis event
        :param wrapped: wrapt's wrapped
        :param instance: wrapt's instance
        :param args: wrapt's args
        :param kwargs: wrapt's kwargs
        :param start_time: Start timestamp (epoch)
        :param response: response data
        :param exception: Exception (if happened)
        """

        super(BaseRedisEvent, self).__init__(start_time)

        self.event_id = 'redis-{}'.format(str(uuid4()))

        host, port, db = _parse_redis_connection(instance)

        self.resource['name'] = host
        self.resource['metadata'] = {
            'Redis Host': host,
            'Redis Port': port,
            'Redis DB Index': db
        }

        if exception is not None:
            self.set_exception(exception, traceback.format_exc())


class RedisSingleExecutionEvent(BaseRedisEvent):
    """
    Represents single execution redis event.
    """

    ORIGIN = 'redis'
    RESOURCE_TYPE = 'redis'

    # pylint: disable=W0613
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

        super(RedisSingleExecutionEvent, self).__init__(
            wrapped, instance, args, kwargs, start_time, response, exception
        )

        self.event_id = 'redis-{}'.format(str(uuid4()))

        operation, key = _parse_redis_cmd(args)
        self.resource['operation'] = operation
        self.resource['metadata']['Redis Key'] = key

        if response:
            add_data_if_needed(
                self.resource['metadata'],
                'redis.response',
                response
            )


class RedisMultiExecutionEvent(BaseRedisEvent):
    """
    Represents base redis event.
    """

    ORIGIN = 'redis'
    RESOURCE_TYPE = 'redis'

    # pylint: disable=W0613
    def __init__(self, wrapped, instance, args, kwargs, start_time, response,
                 exception, command_stack):
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

        super(RedisMultiExecutionEvent, self).__init__(
            wrapped, instance, args, kwargs, start_time, response, exception
        )

        self.resource['operation'] = 'Pipeline'

        operations = [
            '{} {}'.format(op, key) for op, key in [
                _parse_redis_cmd(cmd_args)
                for cmd_args, _ in command_stack
            ]
        ]
        self.resource['metadata']['Stack Count'] = len(operations)
        self.resource['metadata']['Actions'] = operations[:MAX_CMD_PIPELINE]


class RedisMultiEventFactory(object):
    """
    Factory class, generates Redis multi-execution event.
    """
    LAST_STACK = []

    @staticmethod
    def create_event(wrapped, instance, args, kwargs, start_time, response,
                     exception):
        """
        Create a Redis event.
        :param wrapped:
        :param instance:
        :param args:
        :param kwargs:
        :param start_time:
        :param response:
        :param exception:
        :return:
        """
        event = RedisMultiExecutionEvent(
            wrapped,
            instance,
            args,
            kwargs,
            start_time,
            response,
            exception,
            RedisMultiEventFactory.LAST_STACK
        )
        trace_factory.add_event(event)


class RedisSingleEventFactory(object):
    """
    Factory class, generates Redis event.
    """
    @staticmethod
    def create_event(wrapped, instance, args, kwargs, start_time, response,
                     exception):
        """
        Create a Redis event.
        :param wrapped:
        :param instance:
        :param args:
        :param kwargs:
        :param start_time:
        :param response:
        :param exception:
        :return:
        """
        event = RedisSingleExecutionEvent(
            wrapped,
            instance,
            args,
            kwargs,
            start_time,
            response,
            exception
        )
        trace_factory.add_event(event)
