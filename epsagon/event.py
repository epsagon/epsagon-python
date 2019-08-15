"""
Base Event class
"""

from __future__ import absolute_import
import time
from .common import ErrorCode


class BaseEvent(object):
    """
    Represents base trace's event
    """

    ORIGIN = 'base'
    RESOURCE_TYPE = 'base'

    def __init__(self, start_time):
        """
        Initialize.
        :param start_time: event's start time (epoch)
        """

        self.start_time = start_time
        self.event_id = ''
        self.origin = self.ORIGIN
        self.duration = 0.0
        self.error_code = ErrorCode.OK
        self.exception = {}

        self.resource = {
            'type': self.RESOURCE_TYPE,
            'name': '',
            'operation': '',
            'metadata': {},
        }

    @staticmethod
    def load_from_dict(event_data):
        """
        Load Event object from dict.
        :param event_data: dict
        :return: Event
        """

        event = BaseEvent(event_data['start_time'])
        event.event_id = event_data['id']
        event.origin = event_data['origin']
        event.duration = event_data['duration']
        event.error_code = event_data['error_code']
        event.resource = event_data['resource']
        if event.error_code == ErrorCode.EXCEPTION:
            event.exception = event_data['exception']

        return event

    def to_dict(self):
        """
        Converts Event to dict.
        :return: dict
        """

        self_as_dict = {
            'id': self.event_id,
            'start_time': self.start_time,
            'duration': self.duration,
            'origin': self.origin,
            'error_code': self.error_code,
            'resource': self.resource,
        }

        if self.error_code == ErrorCode.EXCEPTION:
            self_as_dict['exception'] = self.exception

        return self_as_dict

    def terminate(self):
        """
        Sets duration time.
        :return: None
        """
        self.duration = time.time() - self.start_time

    def set_error(self):
        """
        Sets general error.
        :return: None
        """

        self.error_code = ErrorCode.ERROR

    def set_exception(self, exception, traceback_data):
        """
        Sets exception data on event.
        :param exception: Exception object
        :param traceback_data: traceback string
        :return: None
        """

        self.error_code = ErrorCode.EXCEPTION
        self.exception['type'] = type(exception).__name__
        self.exception['message'] = str(exception)
        self.exception['traceback'] = traceback_data
        self.exception['time'] = time.time()

    def identifier(self):
        """
        Return event identifier
        :return: event identifier
        """
        return '{}|{}'.format(self.ORIGIN, self.RESOURCE_TYPE)
