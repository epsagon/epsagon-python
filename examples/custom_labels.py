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
    epsagon.label('label', 'something_to_filter_afterwards')
    epsagon.label('number_of_records_parsed_successfully', 42)

    return 'It worked!'


if __name__ == '__main__':
    handle()
