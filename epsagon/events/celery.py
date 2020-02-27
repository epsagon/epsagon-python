from __future__ import absolute_import
import time
import functools
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
        self.resource['operation'] = 'produce'

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

    def finalize(self):
        """
        finalize event.
        :return: None
        """
        self.terminate()


def signal_wrapper(func):
    @functools.wraps(func)
    def _signal_wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except:
            print('test')
    return _signal_wrapper

# -----------------------
#  Celery publish events
# -----------------------

@signal_wrapper
def wrap_before_publish(*args, **kwargs):
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

    event_id = kwargs.get('headers', {}).get('id', '')
    sender = kwargs.get('sender', '')
    event_key = '{}-{}'.format(sender, event_id)
    EVENTS[event_key] = event


@signal_wrapper
def wrap_after_publish(*args, **kwargs):
    event_id = kwargs.get('headers', {}).get('id', '')
    sender = kwargs.get('sender', '')
    event_key = '{}-{}'.format(sender, event_id)
    event = EVENTS.get(event_key)
    if event:
        event.finalize()
        trace_factory.add_event(event)

# ----------------------
#  Celery runner events
# ----------------------


@signal_wrapper
def wrap_prerun(*args, **kwargs):
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
    event_id = kwargs.get('task_id', '')
    sender = kwargs.get('sender').name
    event_key = '{}-{}'.format(sender, event_id)
    EVENTS[event_key] = runner
    trace_factory.set_runner(runner)


@signal_wrapper
def wrap_postrun(*args, **kwargs):
    event_id = kwargs.get('task_id', '')
    sender = kwargs.get('sender').name
    event_key = '{}-{}'.format(sender, event_id)
    event = EVENTS.get(event_key)
    if event:
        event.finalize()
    trace_factory.send_traces()



@signal_wrapper
def wrap_retry(*args, **kwargs):
    print('wrap_retry')
    print(args)
    print(kwargs)
    print('wrap_retry')

@signal_wrapper
def wrap_failure(*args, **kwargs):
    print('wrap_failure')
    print(args)
    print(kwargs)
    print('wrap_failure')