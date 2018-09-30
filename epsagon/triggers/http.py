"""
HTTP triggers for frameworks.
"""

from __future__ import absolute_import
from ..event import BaseEvent


class BaseHTTPTrigger(BaseEvent):
    """
    Represents base HTTP trigger
    """
    ORIGIN = 'trigger'


class SQSHTTPTrigger(BaseHTTPTrigger):
    """
    Represents SQS HTTP trigger
    """
    RESOURCE_TYPE = 'sqs'

    # pylint: disable=W0613
    def __init__(self, start_time, request):
        """
        Initialize.
        :param start_time: event's start time (epoch).
        :param request: HTTP request.
        """

        super(SQSHTTPTrigger, self).__init__(start_time)

        self.event_id = request.headers.get('X-Aws-Sqsd-Msgid')
        self.resource['name'] = request.headers.get('X-Aws-Sqsd-Queue', 'N/A')
        self.resource['operation'] = 'ReceiveMessage'


class HTTPTriggerFactory(object):
    """
    Represents a HTTP Trigger Factory.
    """
    FACTORY = {
        class_obj.RESOURCE_TYPE: class_obj
        for class_obj in BaseHTTPTrigger.__subclasses__()
    }

    @staticmethod
    def factory(start_time, request):
        """
        Creates trigger event object.
        :param start_time: event's start time (epoch)
        :param request: HTTP request.
        :return: Event or None.
        """

        if request.headers.get('X-Aws-Sqsd-Msgid'):
            return SQSHTTPTrigger(start_time, request)
        return None
