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

# Stores all events
EVENTS = {}


class CeleryEvent(BaseEvent):
    """
    Represents Celery event.
    """

    ORIGIN = 'celery'
    RESOURCE_TYPE = 'celery'
    OPERATION = 'publish'

    def __init__(
            self,
            start_time,
            sender,
            routing_key,
            body,
            headers,
            app_conn
    ):
        """
        Initialize.
        """
        super(CeleryEvent, self).__init__(start_time)

        self.event_id = str(uuid4())
        self.resource['name'] = sender
        self.resource['operation'] = self.OPERATION

        self.resource['metadata'] = {
            'origin': headers['origin'],
            'retries': headers['retries'],
            'id': headers['id'],
            'routing_key': routing_key,
            'hostname': app_conn.hostname,
            'driver': app_conn.transport.driver_type,
        }
        add_data_if_needed(
            self.resource['metadata'],
            'body',
            body
        )


def get_event_key(*args, **kwargs):  # pylint: disable=unused-argument
    """
    Returns the event key to get from EVENTS.
    :return: `sender-id` string
    """
    if 'task_id' in kwargs:
        event_id = kwargs.get('task_id', '')
        sender = kwargs.get('sender').name
    elif 'request' in kwargs:
        event_id = kwargs.get('request', {}).get('id', '')
        sender = kwargs.get('sender').name
    else:
        event_id = kwargs.get('headers', {}).get('id', '')
        sender = kwargs.get('sender', '')
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
            event = EVENTS.get(get_event_key(*args, **kwargs))
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
    body = kwargs.get('body', [None])[0]
    if body:
        body = list(body)

    app_conn = import_module('celery').current_app.connection()
    event = CeleryEvent(
        time.time(),
        kwargs.get('sender', ''),
        kwargs.get('routing_key', ''),
        body,
        kwargs.get('headers', ''),
        app_conn,
    )

    EVENTS[get_event_key(*args, **kwargs)] = event


@signal_wrapper
def wrap_after_publish(*args, **kwargs):
    """
    Wraps after publish signal (task.delay or task.apply_async)
    """
    event = EVENTS.get(get_event_key(*args, **kwargs))
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
    app_conn = import_module('celery').current_app.connection()
    trace_factory.prepare()
    runner = CeleryRunner(
        time.time(),
        kwargs.get('sender').name,
        kwargs.get('task_id', ''),
        kwargs.get('args'),
        kwargs.get('retval'),
        kwargs.get('state', ''),
        app_conn,
    )

    EVENTS[get_event_key(*args, **kwargs)] = runner
    trace_factory.set_runner(runner)


@signal_wrapper
def wrap_postrun(*args, **kwargs):
    """
    Wraps post-run signal of worker
    """
    event = EVENTS.get(get_event_key(*args, **kwargs))
    if event:
        event.terminate()
        trace_factory.send_traces()


@signal_wrapper
def wrap_retry(*args, **kwargs):
    """
    Wraps retry signal of worker
    """
    event = EVENTS.get(get_event_key(*args, **kwargs))
    if event:
        event.set_retry(kwargs.get('request', {}).get('retries', 0))


@signal_wrapper
def wrap_failure(*args, **kwargs):
    """
    Wraps failure signal of worker
    """
    event = EVENTS.get(get_event_key(*args, **kwargs))
    if event:
        event.set_exception(
            kwargs.get('exception', Exception),
            traceback.format_exc()
        )
