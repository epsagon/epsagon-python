"""
botocore patcher module
"""

import wrapt
import epsagon


def _botocore_wrapper(wrapped, instance, args, kwargs):
    http, parsed_response = wrapped(*args, **kwargs)
    _, request_data = args
    epsagon.messages_buffer.append({
        'endpoint': instance._endpoint_prefix,
        'transaction_id': epsagon.transaction_id,
        'type': 'botocore',
        'total_time': http.elapsed.total_seconds(),
        'response_metadata': parsed_response['ResponseMetadata'],
        'method': request_data['method'],
        'url': request_data['url'],
        'headers': request_data['headers'],
        'body': request_data['body'],
        'query_string': request_data['query_string'],
    })
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