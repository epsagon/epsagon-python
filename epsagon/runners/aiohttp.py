"""
Runner for a aiohttp Python function
"""

from __future__ import absolute_import
import uuid
from ..event import BaseEvent
from ..utils import add_data_if_needed, normalize_http_url


class AiohttpRunner(BaseEvent):
    """
    Represents Python aiohttp event runner.
    """

    ORIGIN = 'runner'
    RESOURCE_TYPE = 'aiohttp'
    OPERATION = 'request'

    def __init__(self, start_time, request, body, handler):
        """
        Initialize.
        :param start_time: event's start time (epoch).
        :param request: the incoming request.
        :param body: the body of request.
        :param handler: original handler of the request.
        """

        super(AiohttpRunner, self).__init__(start_time)

        self.event_id = str(uuid.uuid4())

        self.resource['name'] = normalize_http_url(request.host)
        self.resource['operation'] = request.method

        self.resource['metadata'].update({
            'Base URL': request.url.host,
            'Path': request.url.path,
            'User Agent': request.headers.get('User-Agent', 'N/A'),
            'Endpoint': handler.__name__,
        })

        if request.query_string:
            self.resource['metadata']['Query String'] = request.query_string

        if request.body_exists:
            add_data_if_needed(
                self.resource['metadata'],
                'Request Data',
                body
            )

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
        body = response.body
        if  response.body.__class__.__name__ == 'StringPayload':
            body = getattr(response.body, '_value')

        add_data_if_needed(
            self.resource['metadata'],
            'Response Data',
            body.decode('utf-8')
        )

        add_data_if_needed(
            self.resource['metadata'],
            'Response Headers',
            dict(response.headers)
        )

        self.resource['metadata']['Status'] = response.status

        if response.status >= 500:
            self.set_error()
