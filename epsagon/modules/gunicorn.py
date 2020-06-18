"""
Gunicorn patcher module.
"""

from __future__ import absolute_import
import warnings
import time
import uuid
import traceback

try:
    from gunicorn.config import (
        PreRequest, validate_callable, PostRequest, validate_post_request
    )
except ImportError:
    class PreRequest(object):
        """
        Dummy PreRequest Class
        """
        def __init__(self):
            pass

    class PostRequest(object):
        """
        Dummy Post Request Class
        """
        def __init__(self):
            pass

    def validate_callable(_):
        """
        Dummy Validate Callable Function
        :param _:
        :return:
        """
        return True

    def validate_post_request(_):
        """
        Dummy Validate Post Request Function
        :param _:
        :return:
        """
        return True

import epsagon
import epsagon.trace
from epsagon.common import EpsagonWarning
from epsagon.utils import collect_container_metadata


from ..event import BaseEvent
from ..http_filters import ignore_request
from ..utils import add_data_if_needed


class GunicornRunner(BaseEvent):
    """
    Represents Python Gunicorn event runner.
    """

    ORIGIN = 'runner'
    RESOURCE_TYPE = 'python_gunicorn'
    OPERATION = 'request'

    def __init__(self, start_time, request):
        """
        Initialize.
        :param start_time: event's start time (epoch).
        :param request: the incoming request.
        """
        super(GunicornRunner, self).__init__(start_time)

        self.event_id = str(uuid.uuid4())

        self.resource['name'] = 'localhost'
        if hasattr(request, 'headers'):
            headers = dict(request.headers)
            self.resource['name'] = (
                headers.get('HOST', 'localhost').split(':')[0]
            )
            add_data_if_needed(
                self.resource['metadata'],
                'Request Headers',
                headers
            )

        self.resource['operation'] = request.method
        self.resource['metadata'].update({'Path': request.path})
        self.resource['metadata'].update({'Query': request.query})

    def update_response(self, response):
        """
        Adds response data to event.
        :param response: WSGI Response
        :return: None
        """
        add_data_if_needed(
            self.resource['metadata'],
            'Response Headers',
            dict(response.headers)
        )

        if response.status_code >= 500:
            self.set_error()


class PreRequestWrapped(PreRequest):
    """
    Represents Gunicorn Middleware's PreRequest Hook
    """
    name = 'pre_request'
    section = 'Server Hooks'
    validator = validate_callable(2)
    type = callable

    # pylint: disable=no-self-argument
    def pre_request(worker, req):
        """
        Runs before process of response.
        """
        if 'SyncWorker' not in type(worker).__name__:
            return

        trace = epsagon.trace.trace_factory.get_or_create_trace()
        trace.prepare()

        if ignore_request('', req.path.lower()):
            return

        # Create a Gunicorn runner with current request.
        try:
            runner = GunicornRunner(
                time.time(),
                req
            )
            trace.set_runner(runner)

            # Collect metadata in case this is a container.
            collect_container_metadata(runner.resource['metadata'])
        # pylint: disable=W0703
        except Exception as exception:
            # Regress to python runner.
            warnings.warn('Could not extract request', EpsagonWarning)
            epsagon.trace.trace_factory.add_exception(
                exception,
                traceback.format_exc()
            )

    # pylint: disable=no-staticmethod-decorator
    default = staticmethod(pre_request)
    desc = """\
        Called just before a worker processes the request.
        The callable needs to accept two instance variables for the Worker and
        the Request.
    """


class PostRequestWrapped(PostRequest):
    """
        Represents Gunicorn Middleware's PostRequest Hook
    """
    name = 'post_request'
    section = 'Server Hooks'
    validator = validate_post_request
    type = callable

    # pylint: disable=no-self-argument
    def post_request(worker, _req, environ, resp):
        """
        Runs after process of response.
        """
        if 'SyncWorker' not in type(worker).__name__:
            return

        # Ignoring non-relevant content types.
        if ignore_request(environ.get('Content-Type', '').lower(), ''):
            return

        trace = epsagon.trace.trace_factory.active_trace
        if trace and trace.runner:
            trace.runner.update_response(resp)
            epsagon.trace.trace_factory.send_traces()

    # pylint: disable=no-staticmethod-decorator
    default = staticmethod(post_request)
    desc = """\
        Called after a worker processes the request.
        The callable needs to accept two instance variables for the Worker and
        the Request.
    """
