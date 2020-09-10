# pylint: disable=protected-access
"""
Runner for a Tornado Python framework
"""

from __future__ import absolute_import
import uuid
from ..event import BaseEvent
from ..utils import add_data_if_needed
from ..constants import EPSAGON_HEADER_TITLE

MAX_PAYLOAD_BYTES = 2000


class TornadoRunner(BaseEvent):
    """
    Represents Python Tornado event runner.
    """

    ORIGIN = 'runner'
    RESOURCE_TYPE = 'python_tornado'

    def __init__(self, start_time, request):
        """
        Initialize.
        :param start_time: event's start time (epoch).
        :param request: the incoming request.
        """

        super(TornadoRunner, self).__init__(start_time)

        self.event_id = str(uuid.uuid4())

        # Since Tornado doesn't has app name, we use the tracer app name.
        self.resource['name'] = request.host
        self.resource['operation'] = request.method

        self.resource['metadata'].update({
            'Host': request.host,
            'url': '{}://{}{}'.format(
                request.protocol,
                request.host,
                request.path
            ),
            'Path': request.path,
            'Version': request.version,
            'Remote IP': request.remote_ip,
            'User Agent': request.headers.get('User-Agent', 'N/A'),
        })

        request_headers = dict(request.headers)

        if request_headers.get(EPSAGON_HEADER_TITLE):
            self.resource['metadata']['http_trace_id'] = (
                request_headers.get(EPSAGON_HEADER_TITLE)
            )

        if request.query:
            add_data_if_needed(
                self.resource['metadata'],
                'Query',
                request.query
            )

        if request_headers:
            add_data_if_needed(
                self.resource['metadata'],
                'Request Headers',
                request_headers
            )

    def update_response(self, response, response_body=None):
        """
        Adds response data to event.
        :param response_body: Response body
        :param response: WSGI Response
        """
        headers = dict(response._headers.get_all())
        add_data_if_needed(
            self.resource['metadata'],
            'Response Headers',
            headers
        )

        if response_body:
            add_data_if_needed(
                self.resource['metadata'],
                'Response Body',
                str(response_body)[:MAX_PAYLOAD_BYTES]
            )

        self.resource['metadata']['status_code'] = response._status_code
        self.resource['metadata']['etag'] = headers.get('Etag')

        if not self.error_code and response._status_code >= 500:
            self.set_error()
