"""
kafka-python patcher module.
"""

from __future__ import absolute_import
import wrapt
from epsagon.modules.general_wrapper import wrapper
from ..events.kafka import KafkaEventFactory
from ..constants import EPSAGON_HEADER
from ..utils import get_epsagon_http_trace_id


def _parse_args(
    topic,
    value=None,
    key=None,
    headers=None,
    partition=None,
    timestamp_ms=None
):
    """Sort and return args and kwargs according to the original signature"""
    return (topic, ), {
        'value': value,
        'key': key,
        'headers': headers,
        'partition': partition,
        'timestamp_ms': timestamp_ms
    }


def _wrapper(wrapped, instance, args, kwargs):
    """KafkaProducer.send wrapper"""
    new_args, new_kwargs = _parse_args(*args, **kwargs)

    # Adds epsagon header only on Kafka record V2. V0/V1 don't support it
    # pylint: disable=protected-access
    if instance._max_usable_produce_magic() == 2:
        if not new_kwargs.get('headers'):
            new_kwargs['headers'] = []
        new_kwargs['headers'].append(
            (EPSAGON_HEADER, get_epsagon_http_trace_id().encode())
        )

    return wrapper(KafkaEventFactory, wrapped, instance, new_args, new_kwargs)


def patch():
    """
    patch module.
    :return: None
    """
    wrapt.wrap_function_wrapper(
        'kafka.producer.kafka',
        'KafkaProducer.send',
        _wrapper
    )
