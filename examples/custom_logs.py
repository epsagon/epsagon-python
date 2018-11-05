"""
Example for custom logs usage in AWS Lambda function.
"""

import epsagon
epsagon.init(
    token='my-secret-token',
    app_name='my-app-name',
    metadata_only=False
)


@epsagon.lambda_wrapper
def handle(event, context):
    epsagon.log('Doing something')
    epsagon.error('Something bad happened')
    return 'It worked!'
