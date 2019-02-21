"""
Simple example for Epsagon usage in Google Cloud Platform function.
"""

import epsagon

epsagon.init(
    token='my-secret-token',
    app_name='my-app-name',
    metadata_only=False
)


@epsagon.gcp_wrapper
def handle(request):
    """
    GCP Function
    :param request: request argument
    :return: It worked!
    """
    return '{} It worked!'.format(request)
