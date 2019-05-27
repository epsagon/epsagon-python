"""
Epsagon Acceptance Tests
"""
import platform
import json
import urllib3
import epsagon


epsagon.init(
    token='acceptance-test',
    app_name='acceptance',
)


@epsagon.lambda_wrapper
def sanity(event, _):
    """
    Basic test, using the Epsagon lambda-wrapper
    :param event: events args
    :param _: context, unused
    :return: Success indication
    """
    body = {
        'message': 'Epsagon: General Acceptance Test (py {})'.format(
            platform.python_version()
        ),
        'input': event
    }

    response = {
        'statusCode': 200,
        'body': json.dumps(body)
    }

    return response


@epsagon.lambda_wrapper
def labels(event, _):
    """
    Test the usage of labels
    :param event: event args
    :param _: context, unused
    :return: Success indication
    """
    body = {
        'message': 'Epsagon: Labels Acceptance Test (py {})'.format(
            platform.python_version()
        ),
        'input': event
    }

    response = {
        'statusCode': 200,
        'body': json.dumps(body)
    }

    epsagon.label('label-key', 'label-value')
    epsagon.label(None, None)
    epsagon.label('label-key', 12)
    epsagon.label(12, 12)
    epsagon.label(12, None)
    epsagon.label('12', None)

    return response


@epsagon.lambda_wrapper
def read_data(event, _):
    """
    Read data from another service
    """
    url = (f'https://{event["headers"]["Host"]}/'
           f'{event["requestContext"]["stage"]}/sanity')
    r = urllib3.PoolManager().request(
        'POST', url,
        body=json.dumps({'hello': 'world'}).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
    )
    data = r.data
    response = {
        'statusCode': 200,
        'body': json.dumps(json.loads(data)['input']),
    }

    return response
