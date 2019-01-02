# pylint: disable=protected-access
"""
Runner for a Tornado Python framework
"""

from __future__ import absolute_import
import uuid
from ..event import BaseEvent
from ..utils import add_data_if_needed


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
        self.resource['name'] = request.path
        self.resource['operation'] = request.method

        self.resource['metadata'] = {
            'Host': request.host,
            'Protocol': request.protocol,
            'Path': request.path,
            'Version': request.version,
            'Remote IP': request.remote_ip,
            'User Agent': request.headers.get('User-Agent', 'N/A'),
        }

        if request.query:
            add_data_if_needed(
                self.resource['metadata'],
                'Query',
                request.query
            )

    def update_response(self, response):
        """
        Adds response data to event.
        :param response: WSGI Response
        """

        headers = dict(response._headers.get_all())
        add_data_if_needed(
            self.resource['metadata'],
            'Response Headers',
            headers
        )

        self.resource['metadata']['Status'] = response._status_code
        self.resource['metadata']['etag'] = headers.get('Etag')

        if not self.error_code and response._status_code >= 300:
            self.set_error()
