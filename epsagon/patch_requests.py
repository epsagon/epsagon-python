"""
requests patcher module
"""

import wrapt
import uuid
import events


def _request_wrapper(wrapped, instance, args, kwargs):
    prepared_request = args[0]
    response = wrapped(*args, **kwargs)
    event = events.Event(
        event_id='r{}'.format(str(uuid.uuid4())),
        event_type='requests',
        service_type=prepared_request.url,
        service_name=prepared_request.url,
        duration=response.elapsed.total_seconds(),
        end_reason=events.Event.ER_OK if response.status_code < 300 else events.Event.ER_EXCEPTION,
        metadata={
            'request_headers': dict(prepared_request.headers),
            'request_body': prepared_request.body,
            'request_method': prepared_request.method,
            'response_headers': dict(response.headers),
            'status_code': response.status_code,
            #'response_body': response.text
        }
    )
    events.events.append(event)
    return response


def patch():
    """
    patch module
    :return: None
    """
    wrapt.wrap_function_wrapper(
        'requests',
        'Session.send',
        _request_wrapper
    )
