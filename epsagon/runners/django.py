"""
Runner for a Django Python function
"""

from __future__ import absolute_import
import uuid
from ..event import BaseEvent
from ..utils import add_data_if_needed


class DjangoRunner(BaseEvent):
    """
    Represents Python Django event runner.
    """

    ORIGIN = 'runner'
    RESOURCE_TYPE = 'python_django'
    OPERATION = 'request'

    def __init__(self, start_time, request):
        """
        Initialize.
        :param start_time: event's start time (epoch).
        :param request: the incoming request.
        """
        super(DjangoRunner, self).__init__(start_time)

        self.event_id = str(uuid.uuid4())
        self.resource['name'] = request.get_host()
        self.resource['operation'] = request.method

        self.resource['metadata'].update({'Path': request.path})

        if request.body:
            add_data_if_needed(
                self.resource['metadata'],
                'Request Data',
                request.body
            )

        # request.headers introduced since django==2.2
        if hasattr(request, 'headers'):
            add_data_if_needed(
                self.resource['metadata'],
                'Request Headers',
                dict(request.headers)
            )

    def update_response(self, response):
        """
        Adds response data to event.
        :param response: WSGI Response
        :return: None
        """
        add_data_if_needed(
            self.resource['metadata'],
            'Response Data',
            response.content
        )

        add_data_if_needed(
            self.resource['metadata'],
            'Response Headers',
            dict(response.items())
        )

        if response.status_code >= 500:
            self.set_error()
