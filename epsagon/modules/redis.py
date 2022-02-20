"""
Redis patcher module.
"""

from __future__ import absolute_import
import copy
import wrapt
from epsagon.modules.general_wrapper import wrapper
from ..events.redis import RedisSingleEventFactory, RedisMultiEventFactory


def _single_wrapper(wrapped, instance, args, kwargs):
    """
    Single execution wrapper for Redis instrumentation.
    :param wrapped: wrapt's wrapped
    :param instance: wrapt's instance
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    :return: None
    """
    return wrapper(RedisSingleEventFactory, wrapped, instance, args, kwargs)


def _multi_wrapper(wrapped, instance, args, kwargs):
    """
    Multi-execution wrapper for Redis instrumentation.
    :param wrapped: wrapt's wrapped
    :param instance: wrapt's instance
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    :return: None
    """
    RedisMultiEventFactory.LAST_STACK = copy.deepcopy(instance.command_stack)
    return wrapper(RedisMultiEventFactory, wrapped, instance, args, kwargs)


def patch():
    """
    patch module.
    :return: None
    """
    wrapt.wrap_function_wrapper(
        'redis',
        'Redis.execute_command',
        _single_wrapper
    )
    wrapt.wrap_function_wrapper(
        'redis.client',
        'Pipeline.immediate_execute_command',
        _single_wrapper
    )
    wrapt.wrap_function_wrapper(
        'redis.client',
        'Pipeline.execute',
        _multi_wrapper
    )
