"""
Runner for a Celery Python function
"""

from __future__ import absolute_import
import time
from uuid import uuid4
from importlib import import_module
from ..event import BaseEvent
from ..utils import add_data_if_needed


class CeleryRunner(BaseEvent):
    """
    Represents Python Celery event runner.
    """

    ORIGIN = 'runner'
    RESOURCE_TYPE = 'celery'
    OPERATION = 'execute'

    def __init__(self, *args, **kwargs):  # pylint: disable=unused-argument
        """
        Initialize.
        :param start_time: event's start time (epoch).
        """

        super(CeleryRunner, self).__init__(time.time())

        self.event_id = str(uuid4())

        self.resource['name'] = (
            kwargs.get('sender').name
            if kwargs.get('sender')
            else ''
        )
        self.resource['operation'] = self.OPERATION

        app_conn = import_module('celery').current_app.connection()
        task_id = kwargs.get('task_id', '')
        body = kwargs.get('args')
        retval = kwargs.get('retval')
        state = kwargs.get('state', '')

        self.resource['metadata'].update({
            'id': task_id,
            'state': state,
            'hostname': app_conn.hostname,
            'virtual_host': app_conn.virtual_host,
            'driver': app_conn.transport.driver_type,
        })

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

    def set_retry(self, attempt_number):
        """
        Setting retry attempt number
        """
        self.resource['metadata']['attempt_number'] = attempt_number
