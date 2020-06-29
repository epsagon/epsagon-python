"""
Triggers for Azure Function
"""

from __future__ import absolute_import
from uuid import uuid4
from epsagon.utils import add_data_if_needed
from ..event import BaseEvent
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse


class BaseAzureTrigger(BaseEvent):
    """
    Represents base Azure Function trigger
    """
    ORIGIN = 'trigger'


class HTTPAzureTrigger(BaseAzureTrigger):
    """
    Represents an HTTP Azure Function trigger.
    """
    RESOURCE_TYPE = 'http'

    def __init__(self, start_time, event, response):
        """
        Initialize.
        :param start_time: event's start time (epoch)
        :param event: event dict from the entry point,
            azure.functions.HttpRequest
        :param response: http response, azure.functions.HttpResponse
        """

        super(HTTPAzureTrigger, self).__init__(start_time)
        self.resource['operation'] = event.method
        url_data = urlparse(event.url)
        self.resource['name'] = url_data.netloc

        self.event_id = event.headers.get('x-arr-log-id', str(uuid4()))

        self.resource['metadata'] = {
            'http.request.path': url_data.path,
            'http.status_code': response.status_code,
        }

        if event.params:
            add_data_if_needed(
                self.resource['metadata'],
                'http.request.path_params',
                dict(event.params.items())
            )

        add_data_if_needed(
            self.resource['metadata'],
            'http.request.headers',
            event.headers.__http_headers__
        )

        add_data_if_needed(
            self.resource['metadata'],
            'http.response.headers',
            response.headers.__http_headers__
        )

        try:
            add_data_if_needed(
                self.resource['metadata'],
                'http.request.body',
                event.get_json()
            )
        except Exception:  # pylint: disable=broad-except
            pass


class AzureTriggerFactory(object):
    """
    Represents a Azure Function trigger Factory.
    """

    @staticmethod
    def factory(start_time, event, result):
        """
        Creates trigger event object.
        :param start_time: event's start time (epoch)
        :param event: event dict from the entry point
        :param result: function result, can be relevant in HTTP
        :return: Event or None
        """
        if 'req' in event:
            return HTTPAzureTrigger(start_time, event['req'], result)
        return None
