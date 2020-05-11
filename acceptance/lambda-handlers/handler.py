"""
Epsagon Acceptance Tests
"""
import platform
import json
import logging
import epsagon

logging.getLogger().setLevel(logging.INFO)


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
def logging_test(event, _):
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
    logging.info(event)

    response = {
        'statusCode': 200,
        'body': json.dumps(body)
    }

    return response
