"""
requests patcher module
"""

import wrapt
import epsagon


def _request_wrapper(wrapped, instance, args, kwargs):
    response = wrapped(*args, **kwargs)
    epsagon.messages_buffer.append({
        'endpoint': args[0].url,
        'type': 'requests',
        'transaction_id': epsagon.transaction_id,
        'status_code': response.status_code,
        'elapsed_seconds': str(response.elapsed.total_seconds()),
    })
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
