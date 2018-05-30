"""
Wrapper for Python Flask.
"""

from __future__ import absolute_import

from flask import request

import traceback
import time
import warnings

import epsagon.trace
import epsagon.triggers.http
import epsagon.runners.flask
from epsagon.common import EpsagonWarning


class EpsagonFlask(object):
    """
    Wraps Flask wsgi application.
    """

    def __init__(self, app):
        """
        WSGI app wrapper for flask application.
        :param app: the :class:`flask.Flask` application object.
        """

        self.app = app

        # Override request handling.
        self.app.before_request(self._before_request)
        self.app.after_request(self._after_request)
        self.app.teardown_request(self._teardown_request)

        self.runner = None

    def _before_request(self):
        """
        Runs when new request comes in.
        :return: None.
        """
        epsagon.trace.tracer.prepare()

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
            epsagon.trace.tracer.add_exception(
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
                epsagon.trace.tracer.add_event(trigger)
        # pylint: disable=W0703
        except Exception as exception:
            epsagon.trace.tracer.add_exception(
                exception,
                traceback.format_exc(),
            )

    def _after_request(self, response):
        """
        Runs after first process of response.
        :param response: The current Response object.
        :return: Response.
        """
        self.runner.update_response(response)
        return response

    def _teardown_request(self, exception):
        """
        Runs at the end of the request. Exception will be passed if happens.
        :param exception: Exception (or None).
        :return: None.
        """

        if exception:
            traceback_data = ''.join(traceback.format_exception(
                type(exception),
                exception,
                exception.__traceback__,
            ))
            self.runner.set_exception(exception, traceback_data)

        epsagon.trace.tracer.add_event(self.runner)
        epsagon.trace.tracer.send_traces()
