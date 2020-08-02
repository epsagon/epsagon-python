"""
Wrapper for Python Flask.
"""

from __future__ import absolute_import
import traceback
import time
import warnings

from flask import request
import epsagon.trace
import epsagon.triggers.http
import epsagon.runners.flask
from epsagon.common import EpsagonWarning
from epsagon.utils import collect_container_metadata,\
    get_traceback_data_from_exception
from ..http_filters import ignore_request


class FlaskWrapper(object):
    """
    Wraps Flask wsgi application.
    """
    EPSAGON_MARKER = '_epsagon_wrapper'

    def __init__(self, app, ignored_endpoints=None):
        """
        WSGI app wrapper for flask application.
        :param app: the :class:`flask.Flask` application object.
        :param ignored_endpoints: endpoint paths to ignore.
        """
        # Wrapping app only once
        if getattr(app, self.EPSAGON_MARKER, False):
            return
        setattr(app, self.EPSAGON_MARKER, True)
        self.app = app
        self.ignored_endpoints = []
        if ignored_endpoints:
            self.ignored_endpoints = ignored_endpoints

        # Override request handling.
        self.app.before_request(self._before_request)
        self.app.after_request(self._after_request)
        self.app.teardown_request(self._teardown_request)

        # Whether we ignore this request or not.
        self.ignored_request = False
        epsagon.trace.trace_factory.switch_to_multiple_traces()

    def _before_request(self):
        """
        Runs when new request comes in.
        :return: None.
        """
        # Ignoring non relevant content types.
        self.ignored_request = ignore_request('', request.path.lower())

        if self.ignored_request:
            return

        trace = epsagon.trace.trace_factory.get_or_create_trace()
        trace.prepare()

        # Create flask runner with current request.
        try:
            runner = epsagon.runners.flask.FlaskRunner(
                time.time(),
                self.app,
                request
            )
            trace.set_runner(runner)

            # Collect metadata in case this is a container.
            collect_container_metadata(runner.resource['metadata'])

        # pylint: disable=W0703
        except Exception as exception:
            # Regress to python runner.
            warnings.warn('Could not extract request', EpsagonWarning)
            trace.add_exception(
                exception,
                traceback.format_exc()
            )

        # Extract HTTP trigger data.
        try:
            trigger = epsagon.triggers.http.HTTPTriggerFactory.factory(
                    time.time(),
                    request
                )
            if trigger:
                trace.add_event(trigger)
        # pylint: disable=W0703
        except Exception as exception:
            trace.add_exception(
                exception,
                traceback.format_exc(),
            )

    def _after_request(self, response):
        """
        Runs after first process of response.
        :param response: The current Response object.
        :return: Response.
        """
        if self.ignored_request:
            return response

        # Ignoring non relevant content types.
        if ignore_request(response.content_type.lower(), ''):
            self.ignored_request = True
            return response

        trace = epsagon.trace.trace_factory.get_or_create_trace()
        trace.runner.update_response(response)
        return response

    def _teardown_request(self, exception):
        """
        Runs at the end of the request. Exception will be passed if happens.
        If no flask url rule exists for a request, then the request trace
        will be passed.
        :param exception: Exception (or None).
        :return: None.
        """

        if self.ignored_request:
            return

        if exception:
            traceback_data = get_traceback_data_from_exception(exception)
            trace = epsagon.trace.trace_factory.get_or_create_trace()
            trace.runner.set_exception(exception, traceback_data)
        # Ignoring endpoint, only if no error happened.
        if (not exception and
            request.url_rule and
            request.url_rule.rule in self.ignored_endpoints
        ):
            return

        epsagon.trace.trace_factory.send_traces()
