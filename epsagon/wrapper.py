"""
Main Epsagon agent module
"""

import time
import uuid
import functools
import traceback
from epsagon.patcher import patch_all
from epsagon import events


def lambda_wrapper(app_name, token):
    def _lambda_decorator(func):
        @functools.wraps(func)
        def _lambda_wrapper(*args, **kwargs):
            event, context = args

            # Setting for later use
            events.transaction_id = str(uuid.uuid4())
            events.function_name = context.__dict__['function_name']
            events.app_name = app_name
            events.token = token

            event = events.Event(
                event_id=context.__dict__['aws_request_id'],
                event_type='lambda_init',
                service_type='lambda',
                service_name=events.function_name,
                duration=0,
                end_reason=events.Event.ER_OK,
                metadata={
                    'event': event,
                    'log_stream_name': context.__dict__['log_stream_name'],
                    'function_version': context.__dict__['function_version'],
                }
            )

            exception = None
            try:
                result = func(*args, **kwargs)
            except Exception, ex:
                event.end_reason = events.Event.ER_EXCEPTION
                event.metadata['exception'] = ex.message
                event.metadata['traceback'] = traceback.format_exc()
                exception = ex

            event.duration = time.time() - event.timestamp
            events.events.insert(0, event)
            try:
                events.send_to_server()
            except Exception, ex:
                return result

            if exception is None:
                return result
            else:
                raise exception
        return _lambda_wrapper
    return _lambda_decorator

patch_all()
