"""
Runner for a fastapi Python function
"""

from __future__ import absolute_import
import json
import uuid
import warnings
from fastapi.responses import (
    Response,
    JSONResponse,
    HTMLResponse,
    PlainTextResponse,
    UJSONResponse,
    RedirectResponse,
)
from fastapi.encoders import jsonable_encoder
from epsagon.common import EpsagonWarning
from ..event import BaseEvent
from ..utils import add_data_if_needed, normalize_http_url, print_debug
from ..constants import EPSAGON_HEADER

SUPPORTED_RAW_RESPONSE_TYPES = (
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

    def __init__(self, start_time, request):
        """
        Initialize.
        :param start_time: event's start time (epoch).
        :param request: the incoming request.
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

    def update_request_body(self, body):
        """
        Adds request body to event
        """
        if body:
            add_data_if_needed(
                self.resource['metadata'],
                'Request Data',
                body
            )

    def _update_raw_response_body(self, response, response_type):
        """
        Updates the response body by given `raw` response and its type
        """
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


    def update_status_code(self, status_code, override=True):
        """
        Updates the event with given status code.
        :param override: indicates whether to override existing status code
        """
        if self.resource['metadata'].get('status_code') and not override:
            return
        self.resource['metadata']['status_code'] = status_code
        if status_code and status_code >= 500:
            self.set_error()

    def _update_raw_response(self, response):
        """
        Updates the event with data by given raw response.
        Raw response is an instance of Response.
        """
        for response_type in SUPPORTED_RAW_RESPONSE_TYPES:
            if isinstance(response, response_type):
                self._update_raw_response_body(response, response_type)
                break

        response_headers = dict(response.headers.items())
        if response.headers:
            add_data_if_needed(
                self.resource['metadata'],
                'Response Headers',
                response_headers
            )
        self.update_status_code(response.status_code)

    def update_response(self, response, status_code=None):
        """
        Adds response data to event.
        """
        if isinstance(response, Response):
            self._update_raw_response(response)
        else:
            try:
                add_data_if_needed(
                    self.resource['metadata'],
                    'Response Data',
                    jsonable_encoder(response)
                )
            except Exception: # pylint: disable=W0703
                print_debug(
                    'Could not json encode fastapi handler response data'
                )
            if status_code:
                self.update_status_code(status_code)
