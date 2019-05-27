import os
import json
import urllib3
import pytest
import boto3

SERVICE_PREFIX = 'epsagon-acceptance-{}-{}'.format(
    os.environ.get('TRAVIS_BUILD_NUMBER', ''),
    os.environ.get('runtimeName', '')
)


def invoke(name, payload):
    """
    invokes a lambda
    :param name: the name of the lambda to invoke
    :param payload: the payload
    :return: the response
    """
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    return lambda_client.invoke(
        FunctionName='{}-{}'.format(SERVICE_PREFIX, name),
        InvocationType='RequestResponse',
        Payload=payload
    )


class TestLambdaWrapper:
    @pytest.mark.parametrize("input", [
        '',
        '{afwe',
        [],
        [1, 2, 3],
        {},
        {'test': 'test'},
        {'test': 'test', 'more': [1, 2, '3']},
    ])
    def test_sanity_valid_input(self, input):
        response = invoke('sanity', json.dumps(input))
        assert response['StatusCode'] == 200
        content = json.loads(response['Payload'].read())
        assert content['statusCode'] == 200
        body = json.loads(content['body'])
        assert body['input'] == input

    @pytest.mark.parametrize("input", [
        '',
        '{afwe',
        [],
        [1, 2, 3],
        {},
        {'test': 'test'},
        {'test': 'test', 'more': [1, 2, '3']},
    ])
    def test_labels(self, input):
        response = invoke('labels', json.dumps(input))
        assert response['StatusCode'] == 200
        content = json.loads(response['Payload'].read())
        assert content['statusCode'] == 200
        body = json.loads(content['body'])
        assert body['input'] == input


class TestHTTPWrappers:
    """ test http wrappers """
    @staticmethod
    def test_sanity_http():
        """ sanity test """
        # pylint: disable=possibly-unused-variable
        domain = os.getenv('DOMAIN_CODE')
        build_number = os.getenv('TRAVIS_BUILD_NUMBER')
        runtime = os.getenv('runtimeName')
        http_test_url = ('https://{domain}'
                         '.execute-api.us-east-1.amazonaws.com'
                         '/{build_number}-{runtime}'
                         '/http_test'
                         ).format_map(locals())
        response = urllib3.PoolManager().request(
            'GET', http_test_url)
        assert response.status == 200
        content = json.loads(response.data)
        assert json.loads(content['body']) == {'hello': 'world'}
