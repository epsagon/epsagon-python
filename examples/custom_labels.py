"""
Example for custom labels usage in AWS Lambda function.
"""

import epsagon
epsagon.init(
    token='my-secret-token',
    app_name='my-app-name',
    metadata_only=False
)


@epsagon.lambda_wrapper
def handle():
    epsagon.label('first_label', 'value1')
    epsagon.label('second_label', 'value2')

    return 'It worked!'

if __name__ == '__main__':
    handle()
