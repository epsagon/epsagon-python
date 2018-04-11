"""
Simple example for Epsagon usage in AWS Lambda function
"""

import epsagon
epsagon.init(
    token='my-secret-token',
    app_name='my-app-name',
    metadata_only=False
)


@epsagon.lambda_wrapper
def handle(event, context):
    return 'It worked!'
