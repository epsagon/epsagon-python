"""
Wrapper for Django.
"""
from __future__ import absolute_import

import time
import traceback
import warnings
import epsagon
import epsagon.trace
import epsagon.triggers.http
import epsagon.runners.django

from epsagon.common import EpsagonWarning
from epsagon.utils import (
    collect_container_metadata,
    get_traceback_data_from_exception,
)
from ..http_filters import ignore_request


class DjangoMiddleware(object):
    """
    Represents a Django Middleware for Epsagon instrumentation.
    """

    def __init__(self, get_response):
        self.get_response = get_response

        epsagon.trace.trace_factory.switch_to_multiple_traces()

    # pylint: disable=no-self-use
    def process_exception(self, request, process_exception):
        """
        Processes and appends a given exception to the current trace
        """
        if not process_exception:
            return

        if (
                not hasattr(request, 'epsagon_trace') or
                not request.epsagon_trace.runner
        ):
            return

        traceback_data = get_traceback_data_from_exception(process_exception)

        request.epsagon_trace.runner.set_exception(
            process_exception,
            traceback_data,
            False
        )

    def __call__(self, request):
        # Link epsagon to the request object for easy-access to epsagon lib
        request.epsagon = epsagon

        if epsagon.http_filters.is_ignored_endpoint(request.path):
            return self.get_response(request)

        request_middleware = DjangoRequestMiddleware(request)
        request_middleware.before_request()

        response = self.get_response(request)

        request_middleware.after_request(response)
        return response


class DjangoRequestMiddleware(object):
    """
    Django middleware for a single request
    """

    def __init__(self, request):
        self.request = request
        self.runner = None
        self.ignored_request = False

    def before_request(self):
        """
        Runs before process of response.
        """
        trace = epsagon.trace.trace_factory.get_or_create_trace()
        trace.prepare()

        # Ignoring non relevant content types.
        self.ignored_request = ignore_request('', self.request.path.lower())

        if self.ignored_request:
            return

        # Create a Django runner with current request.
        try:
            self.runner = epsagon.runners.django.DjangoRunner(
                time.time(),
                self.request
            )
            trace.set_runner(self.runner)

            # Collect metadata in case this is a container.
            collect_container_metadata(self.runner.resource['metadata'])

        # pylint: disable=W0703
        except Exception as exception:
            # Regress to python runner.
            warnings.warn('Could not extract request', EpsagonWarning)
            epsagon.trace.trace_factory.add_exception(
                exception,
                traceback.format_exc()
            )

        # Extract HTTP trigger data.
        try:
            trigger = epsagon.triggers.http.HTTPTriggerFactory.factory(
                time.time(),
                self.request
            )
            if trigger:
                epsagon.trace.trace_factory.add_event(trigger)
        # pylint: disable=W0703
        except Exception as exception:
            epsagon.trace.trace_factory.add_exception(
                exception,
                traceback.format_exc(),
            )

    def after_request(self, response):
        """
        Runs after process of response.
        """
        if self.ignored_request:
            return

        # Ignoring non relevant content types.
        if ignore_request(response.get('Content-Type', '').lower(), ''):
            self.ignored_request = True
            return

        # Safety in case we run on an old Django version
        if not self.runner:
            return

        self.runner.update_response(response)
        epsagon.trace.trace_factory.send_traces()
