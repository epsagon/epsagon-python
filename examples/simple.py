"""
Simple example for epsagon
"""

import epsagon
epsagon.init(
    token='my-secret-token',
    app_name='my-app-name',  # Optional
)

@epsagon.lambda_wrapper
def handle(event, context):
    return 'It worked!'
