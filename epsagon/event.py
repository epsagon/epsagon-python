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
        event.event_id = event_data['event_id']
        event.origin = event_data['origin']
        event.duration = event_data['duration']
        event.error_code = event_data['error_code']
        event.resource = event_data['resource']
        return event

    def to_dict(self):
        """
        Converts Event to dict.
        :return: dict
        """

        return {
            'id': self.event_id,
            'start_time': self.start_time,
            'duration': self.duration,
            'origin': self.origin,
            'error_code': self.error_code,
            'resource': self.resource,
        }

    def terminate(self):
        """
        Sets duration time.
        :return: None
        """
        self.duration = time.time() - self.start_time

    def set_error(self):
        """
        Sets error.
        :return: None
        """
        self.error_code = ErrorCode.ERROR
