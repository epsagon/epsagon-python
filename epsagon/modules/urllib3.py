"""
urllib3 patcher module.
"""

from __future__ import absolute_import
import uuid
import wrapt
from epsagon.modules.general_wrapper import wrapper
from ..events.urllib3 import Urllib3EventFactory
from ..http_filters import is_blacklisted_url


def _wrapper(wrapped, instance, args, kwargs):
    """
    General wrapper for requests instrumentation.
    :param wrapped: wrapt's wrapped
    :param instance: wrapt's instance
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    :return: None
    """
    # Inject header to support tracing over HTTP requests to
    # opentracing monitored code
    trace_id = uuid.uuid4().hex
    span_id = uuid.uuid4().hex[16:]
    parent_span_id = uuid.uuid4().hex[16:]

    host_url = '{}://{}'.format(instance.scheme, instance.host)

    # Detect if URL is blacklisted, and ignore.
    if not is_blacklisted_url(host_url):
        headers = kwargs.setdefault('headers', {})
        headers['epsagon-trace-id'] = (
            '{trace_id}:{span_id}:{parent_span_id}:1'.format(
                trace_id=trace_id,
                span_id=span_id,
                parent_span_id=parent_span_id
            )
        )

    return wrapper(Urllib3EventFactory, wrapped, instance, args, kwargs)


def patch():
    """
    Patch module.
    :return: None
    """

    try:
        wrapt.wrap_function_wrapper(
            'urllib3',
            'HTTPConnectionPool.urlopen',
            _wrapper
        )
    except Exception:  # pylint: disable=broad-except
        # Can happen in different Python versions.
        pass
