"""
botocore patcher module
"""

import wrapt
import time
import events

# TODO: Fill read end reason by parsed_response['ResponseMetadata']['HTTPStatusCode'] - http://botocore.readthedocs.io/en/latest/client_upgrades.html#error-handling
AWS_TIME_FORMAT = '%a, %d %b %Y %H:%M:%S GMT'

def _botocore_wrapper(wrapped, instance, args, kwargs):
    http, parsed_response = wrapped(*args, **kwargs)
    _, request_data = args
    event = events.Event(
        event_id=parsed_response['ResponseMetadata']['RequestId'],
        event_type='botocore',
        service_type=instance._endpoint_prefix,
        service_name=request_data['url_path'],
        duration=http.elapsed.total_seconds(),
        end_reason=events.Event.ER_OK,
        metadata={
            'response': parsed_response['ResponseMetadata'],
            'method': request_data['method'],
            'url': request_data['url'],
            'headers': request_data['headers'],
            'body': request_data['body'],
            'query_string': request_data['query_string'],
            'region_name': request_data['context']['client_region']
        },
        timestamp=time.mktime(time.strptime(
            parsed_response['ResponseMetadata']['HTTPHeaders']['date'],
            AWS_TIME_FORMAT
        ))
    )
    events.events.append(event)
    return http, parsed_response


def patch():
    """
    patch module
    :return: None
    """
    wrapt.wrap_function_wrapper(
        'botocore.endpoint',
        'Endpoint.make_request',
        _botocore_wrapper
    )