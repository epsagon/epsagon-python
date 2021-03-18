"""
Runner for a Flask Python function
"""

from __future__ import absolute_import
import os
import uuid
from ..event import BaseEvent
from ..utils import add_data_if_needed, normalize_http_url
from ..constants import EPSAGON_HEADER_TITLE


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
            normalize_http_url(request.headers.get('Host'))
            if request.headers and request.headers.get('Host')
            else app.name
        )
        self.resource['operation'] = request.method

        self.resource['metadata'].update({
            'Base URL': request.base_url,
            'Path': request.path,
            'User Agent': request.headers.get('User-Agent', 'N/A'),
            'Flask Application': app.name,
            'Endpoint': request.endpoint,
        })

        if request.query_string:
            self.resource['metadata']['Query String'] = request.query_string

        if request.data:
            add_data_if_needed(
                self.resource['metadata'],
                'Request Data',
                request.data
            )

        request_headers = dict(request.headers)
        if request_headers.get(EPSAGON_HEADER_TITLE):
            self.resource['metadata']['http_trace_id'] = request_headers.get(
                EPSAGON_HEADER_TITLE
            )

        if request_headers:
            add_data_if_needed(
                self.resource['metadata'],
                'Request Headers',
                request_headers
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

        # In some cases capturing the data messes with the original sequence
        # (`direct_passthrough`). So we let the user configure this

        if os.getenv('EPSAGON_IGNORE_FLASK_RESPONSE', '').upper() != 'TRUE':
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

        self.resource['metadata']['status_code'] = response.status

        if response.status_code >= 500:
            self.set_error()
