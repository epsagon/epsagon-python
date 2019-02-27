"""
Runner for a Flask Python function
"""

from __future__ import absolute_import
import uuid
from ..event import BaseEvent
from ..utils import add_data_if_needed


class FlaskRunner(BaseEvent):
    """
    Represents Python Flask event runner.
    """

    ORIGIN = 'runner'
    RESOURCE_TYPE = 'python_flask'
    OPERATION = 'request'

    def __init__(self, start_time, app, request):
        """
        Initialize.
        :param start_time: event's start time (epoch).
        :param app: the flask application.
        :param request: the incoming request.
        """

        super(FlaskRunner, self).__init__(start_time)

        self.event_id = str(uuid.uuid4())

        self.resource['name'] = (
            ' '.join((app.name, request.url_rule.rule))
            if request.url_rule
            else app.name
        )
        self.resource['operation'] = request.method

        self.resource['metadata'] = {
            'Base URL': request.base_url,
            'Path': request.path,
            'User Agent': request.headers.get('User-Agent', 'N/A'),
        }

        if request.query_string:
            self.resource['metadata']['Query String'] = request.query_string

        if request.data:
            add_data_if_needed(
                self.resource['metadata'],
                'Request Data',
                request.data
            )

        add_data_if_needed(
            self.resource['metadata'],
            'Request Headers',
            dict(request.headers)
        )

        if request.values:
            add_data_if_needed(
                self.resource['metadata'],
                'Request Values',
                dict(request.values)
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
            response.data
        )

        add_data_if_needed(
            self.resource['metadata'],
            'Response Headers',
            dict(response.headers)
        )

        self.resource['metadata']['Status'] = response.status

        if response.status_code >= 300:
            self.set_error()
