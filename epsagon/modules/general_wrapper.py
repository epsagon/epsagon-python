"""
General wrapper for instrumentation.
"""

from __future__ import absolute_import
import time
import traceback
from epsagon.trace import tracer


def wrapper(factory, wrapped, instance, args, kwargs):
    """
    General wrapper for instrumentation.
    :param factory: Factory class for the event type
    :param wrapped: wrapt's wrapped
    :param instance: wrapt's instance
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    :return: None
    """

    response = None
    exception = None
    start_time = time.time()

    try:
        response = wrapped(*args, **kwargs)
        return response
    except Exception as exception:
        raise exception
    finally:
        try:
            factory.create_event(
                wrapped,
                instance,
                args,
                kwargs,
                start_time,
                response,
                exception
            )
        except Exception as exception:
            exception_dict = {
                'exception': repr(exception),
                'traceback': traceback.format_exc()
            }
            tracer.exceptions.append(exception_dict)
