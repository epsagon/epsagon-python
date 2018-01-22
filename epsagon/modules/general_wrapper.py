from __future__ import absolute_import

import traceback
from epsagon.trace import tracer


def wrapper(factory, exception_type, wrapped, instance, args, kwargs):
    response = None
    exception = None
    try:
        response = wrapped(*args, **kwargs)
        return response
    except exception_type as exception:
        raise exception
    finally:
        try:
            factory.create_event(
                wrapped,
                instance,
                args,
                kwargs,
                response,
                exception
            )
        except Exception as e:
            exception_dict = {
                'message': e.message,
                'args': e.args,
                'traceback': traceback.format_exc()
            }
            tracer.exceptions.append(exception_dict)
