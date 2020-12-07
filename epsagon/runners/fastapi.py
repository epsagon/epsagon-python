"""
Runner for a fastapi Python function
"""

from __future__ import absolute_import
import json
import uuid
import warnings
from fastapi.responses import (
    JSONResponse,
    HTMLResponse,
    PlainTextResponse,
    UJSONResponse,
    RedirectResponse,
)
from epsagon.common import EpsagonWarning
from ..event import BaseEvent
from ..utils import add_data_if_needed, normalize_http_url
from ..constants import EPSAGON_HEADER

SUPPORTED_RESPONSE_TYPES = (
    JSONResponse,
    HTMLResponse,
    PlainTextResponse,
    UJSONResponse,
    RedirectResponse,
)

class FastapiRunner(BaseEvent):
    """
    Represents Python FastAPI event runner.
    """

    ORIGIN = 'runner'
    RESOURCE_TYPE = 'fastapi'
    OPERATION = 'request'

    def __init__(self, start_time, request, body):
        """
        Initialize.
        :param start_time: event's start time (epoch).
        :param request: the incoming request.
        :param body: the body of request.
        """

        super(FastapiRunner, self).__init__(start_time)

        self.event_id = str(uuid.uuid4())

        self.resource['name'] = normalize_http_url(request.client.host)
        self.resource['operation'] = request.method

        self.resource['metadata'].update({
            'Base URL': str(request.base_url),
            'Path': request.url.path,
            'User Agent': request.headers.get('User-Agent', 'N/A'),
        })

        query_params = request.query_params
        if query_params:
            self.resource['metadata']['Query Params'] = dict(
                query_params.items()
            )

        if body:
            add_data_if_needed(
                self.resource['metadata'],
                'Request Data',
                body
            )

        request_headers = dict(request.headers.items())
        if request_headers.get(EPSAGON_HEADER):
            self.resource['metadata']['http_trace_id'] = request_headers.get(
                EPSAGON_HEADER
            )
        if request_headers:
            add_data_if_needed(
                self.resource['metadata'],
                'Request Headers',
                request_headers
            )

    def update_response(self, response):
        """
        Adds response data to event.
        """
        for response_type in SUPPORTED_RESPONSE_TYPES:
            if isinstance(response, response_type):
                body = response.body
                if response_type == JSONResponse:
                    try:
                        body = json.loads(body)
                    except Exception: # pylint: disable=W0703
                        warnings.warn(
                            'Could not load response json',
                            EpsagonWarning
                        )
                        body = body.decode('utf-8')
                else:
                    body = body.decode('utf-8')
                add_data_if_needed(
                    self.resource['metadata'],
                    'Response Data',
                    body
                )

        response_headers = dict(response.headers.items())
        if response.headers:
            add_data_if_needed(
                self.resource['metadata'],
                'Response Headers',
                response_headers
            )

        self.resource['metadata']['status_code'] = response.status_code

        if response.status_code >= 500:
            self.set_error()
