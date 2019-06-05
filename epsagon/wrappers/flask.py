"""
Wrapper for Python Flask.
"""

from __future__ import absolute_import
import sys
import traceback
import time
import warnings
import six

from flask import request
import epsagon.trace
import epsagon.triggers.http
import epsagon.runners.flask
from epsagon.common import EpsagonWarning
from .http_filters import ignore_request


class FlaskWrapper(object):
    """
    Wraps Flask wsgi application.
    """

    def __init__(self, app, ignored_endpoints=None):
        """
        WSGI app wrapper for flask application.
        :param app: the :class:`flask.Flask` application object.
        :param ignored_endpoints: endpoint paths to ignore.
        """

        self.app = app
        self.ignored_endpoints = []
        if ignored_endpoints:
            self.ignored_endpoints = ignored_endpoints

        # Override request handling.
        self.app.before_request(self._before_request)
        self.app.after_request(self._after_request)
        self.app.teardown_request(self._teardown_request)

        self.exception_handler = {
            2: self._collect_exception_python2,
            3: self._collect_exception_python3,
        }
        self.runner = None

        # Whether we ignore this request or not.
        self.ignored_request = False

    def _before_request(self):
        """
        Runs when new request comes in.
        :return: None.
        """
        trace = epsagon.trace.trace_factory.get_or_create_trace()
        trace.prepare()

        # Ignoring non relevant content types.
        self.ignored_request = ignore_request('', request.path.lower())

        if self.ignored_request:
            return

        # Create flask runner with current request.
        try:
            self.runner = epsagon.runners.flask.FlaskRunner(
                time.time(),
                self.app,
                request
            )
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

        self.runner.update_response(response)
        return response

    def _collect_exception_python3(self, exception):
        """
        Collect exception from exception __traceback__.
        :param exception: Exception from Flask.
        :return: None
        """

        traceback_data = ''.join(traceback.format_exception(
            type(exception),
            exception,
            exception.__traceback__,
        ))
        self.runner.set_exception(exception, traceback_data)

    def _collect_exception_python2(self, exception):
        """
        Collect exception from exception sys.exc_info.
        :param exception: Exception from Flask.
        :return: None
        """

        traceback_data = six.StringIO()
        traceback.print_exception(*sys.exc_info(), file=traceback_data)
        self.runner.set_exception(exception, traceback_data.getvalue())

    def _teardown_request(self, exception):
        """
        Runs at the end of the request. Exception will be passed if happens.
        :param exception: Exception (or None).
        :return: None.
        """

        if self.ignored_request:
            return

        if exception:
            self.exception_handler[sys.version_info.major](exception)

        # Ignoring endpoint, only if no error happened.
        if not exception and request.url_rule.rule in self.ignored_endpoints:
            return

        trace = epsagon.trace.trace_factory.get_or_create_trace()
        trace.add_event(self.runner)
        trace.send_traces()
        trace.prepare()
