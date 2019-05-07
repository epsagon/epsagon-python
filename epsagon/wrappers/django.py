"""
Wrapper for Django.
"""
from __future__ import absolute_import

import time
import traceback
import warnings
import epsagon.trace
import epsagon.triggers.http
import epsagon.runners.django

from epsagon.common import EpsagonWarning
from .http_filters import ignore_request


class DjangoMiddleware(object):
    """
    Represents a Django Middleware for Epsagon instrumentation.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.runner = None
        self.request = None
        self.response = None

        self.ignored_request = False

    def __call__(self, request):
        self.request = request
        self._before_request()

        self.response = self.get_response(request)

        self._after_request()

        return self.response

    def _before_request(self):
        """
        Runs before process of response.
        """
        import threading
        print(threading.get_ident())
        epsagon.trace.factory.get_trace().prepare()
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
        # pylint: disable=W0703
        except Exception as exception:
            # Regress to python runner.
            warnings.warn('Could not extract request', EpsagonWarning)
            epsagon.trace.factory.get_trace().add_exception(
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
                epsagon.trace.factory.get_trace().add_event(trigger)
        # pylint: disable=W0703
        except Exception as exception:
            epsagon.trace.factory.get_trace().add_exception(
                exception,
                traceback.format_exc(),
            )

    def _after_request(self):
        """
        Runs after process of response.
        """
        if self.ignored_request:
            return

        # Ignoring non relevant content typoes.
        if ignore_request(self.response.get('Content-Type').lower(), ''):
            self.ignored_request = True
            return

        epsagon.trace.factory.get_trace().add_event(self.runner)
        self.runner.update_response(self.response)
        epsagon.trace.factory.get_trace().send_traces()
