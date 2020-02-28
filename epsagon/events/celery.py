"""
Celery events module
"""

from __future__ import absolute_import
import time
import functools
import traceback
from uuid import uuid4
from importlib import import_module
from ..trace import trace_factory
from ..event import BaseEvent
from ..utils import add_data_if_needed
from ..runners.celery import CeleryRunner

# A map of all active events and pending runners. The key is the `{sender}-{id}`
ACTIVE_EVENTS = {}


class CeleryEvent(BaseEvent):
    """
    Represents Celery event.
    """

    ORIGIN = 'celery'
    RESOURCE_TYPE = 'celery'
    OPERATION = 'publish'
    DRIVER_MAPPING = {
        'amqp': 'rabbitmq',
        'redis': 'redis',
    }

    def __init__(self, *args, **kwargs):  # pylint: disable=unused-argument
        """
        Initialize.
        """
        super(CeleryEvent, self).__init__(time.time())

        self.event_id = str(uuid4())
        self.resource['name'] = kwargs.get('sender', '')
        self.resource['operation'] = self.OPERATION

        body = kwargs.get('body', [None])[0]
        if body:
            # Body comes in tuple which is not serializable
            # so we change it to list
            body = list(body)

        app_conn = import_module('celery').current_app.connection()
        headers = kwargs.get('headers', {})

        self.resource['metadata'] = {
            'origin': headers.get('origin', ''),
            'retries': headers.get('retries', ''),
            'id': headers.get('id', ''),
            'routing_key': kwargs.get('routing_key', ''),
            'hostname': app_conn.hostname,
            'virtual_host': app_conn.virtual_host,
            'driver': app_conn.transport.driver_type,
        }

        # Check if this is a known driver to update the resource details
        driver_map = self.DRIVER_MAPPING.get(app_conn.transport.driver_type)
        if driver_map:
            self.resource['name'] = app_conn.hostname
            self.resource['type'] = '{}_{}'.format(
                self.RESOURCE_TYPE,
                driver_map
            )

        add_data_if_needed(
            self.resource['metadata'],
            'body',
            body
        )


def get_event_key(*args, **kwargs):  # pylint: disable=unused-argument
    """
    Returns the event key to get from ACTIVE_EVENTS.
    :return: `sender-id` string or None if input does not match
    """
    if 'task_id' in kwargs:
        # Comes from pre and post run, and failure signals
        event_id = kwargs.get('task_id', '')
        sender = kwargs.get('sender').name if kwargs.get('sender') else ''
    elif 'request' in kwargs:
        # Comes from retry signals
        event_id = kwargs.get('request', {}).get('id', '')
        sender = kwargs.get('sender').name if kwargs.get('sender') else ''
    else:
        # Comes from before and after publish signals
        event_id = kwargs.get('headers', {}).get('id', '')
        sender = kwargs.get('sender', '')

    if event_id == '' or sender == '':
        return None

    return '{}-{}'.format(sender, event_id)


def signal_wrapper(func):
    """
    Signal fail-safe wrapper
    :param func: original signal
    :return: fail-safe signal function
    """
    @functools.wraps(func)
    def _signal_wrapper(*args, **kwargs):
        """
        Wraps original signal wrapper with try
        """
        try:
            return func(*args, **kwargs)
        except Exception as exception:  # pylint: disable=broad-except
            event = ACTIVE_EVENTS.get(get_event_key(*args, **kwargs))
            if event:
                trace_factory.add_exception(
                    exception,
                    traceback.format_exc()
                )

    return _signal_wrapper


# -----------------------
#  Celery publish events
# -----------------------

@signal_wrapper
def wrap_before_publish(*args, **kwargs):
    """
    Wraps before publish signal (task.delay or task.apply_async)
    """
    event_key = get_event_key(*args, **kwargs)
    if event_key:
        ACTIVE_EVENTS[event_key] = CeleryEvent(*args, **kwargs)


@signal_wrapper
def wrap_after_publish(*args, **kwargs):
    """
    Wraps after publish signal (task.delay or task.apply_async)
    """
    event_key = get_event_key(*args, **kwargs)
    event = ACTIVE_EVENTS.pop(event_key, None)
    if event:
        event.terminate()
        trace_factory.add_event(event)


# ----------------------
#  Celery runner events
# ----------------------

@signal_wrapper
def wrap_prerun(*args, **kwargs):
    """
    Wraps pre-run signal of worker
    """
    event_key = get_event_key(*args, **kwargs)
    if event_key:
        trace_factory.prepare()
        runner = CeleryRunner(*args, **kwargs)
        ACTIVE_EVENTS[event_key] = runner
        trace_factory.set_runner(runner)


@signal_wrapper
def wrap_postrun(*args, **kwargs):
    """
    Wraps post-run signal of worker
    """
    event_key = get_event_key(*args, **kwargs)
    event = ACTIVE_EVENTS.pop(event_key, None)
    if event:
        event.terminate()
        trace_factory.send_traces()


@signal_wrapper
def wrap_retry(*args, **kwargs):
    """
    Wraps retry signal of worker
    """
    event = ACTIVE_EVENTS.get(get_event_key(*args, **kwargs))
    if event:
        event.set_retry(kwargs.get('request', {}).get('retries', 0))


@signal_wrapper
def wrap_failure(*args, **kwargs):
    """
    Wraps failure signal of worker
    """
    event = ACTIVE_EVENTS.get(get_event_key(*args, **kwargs))
    if event:
        event.set_exception(
            kwargs.get('exception', Exception),
            traceback.format_exc()
        )
