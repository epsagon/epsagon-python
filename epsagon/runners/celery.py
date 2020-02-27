"""
Runner for a Celery Python function
"""

from __future__ import absolute_import
from uuid import uuid4
from ..event import BaseEvent
from ..utils import add_data_if_needed


class CeleryRunner(BaseEvent):
    """
    Represents Python Celery event runner.
    """

    ORIGIN = 'runner'
    RESOURCE_TYPE = 'python_celery'
    OPERATION = 'execute'

    def __init__(
            self,
            start_time,
            sender,
            task_id,
            body,
            retval,
            state,
            app_conn
    ):
        """
        Initialize.
        :param start_time: event's start time (epoch).
        """

        super(CeleryRunner, self).__init__(start_time)

        self.event_id = str(uuid4())

        self.resource['name'] = sender
        self.resource['operation'] = self.OPERATION

        self.resource['metadata'] = {
            'id': task_id,
            'state': state,
            'hostname': app_conn.hostname,
            'driver': app_conn.transport.driver_type,
        }

        if body:
            add_data_if_needed(
                self.resource['metadata'],
                'args',
                body
            )

        if retval:
            add_data_if_needed(
                self.resource['metadata'],
                'retval',
                retval
            )

    def finalize(self):
        """
        Adds response data to event.
        :return: None
        """
        self.terminate()

