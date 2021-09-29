"""
AWS SecretsManager tests
"""
import sys
from moto import mock_secretsmanager
import boto3
from epsagon.trace import trace_factory
from epsagon.events.botocore import BotocoreSecretsManagerEvent

TEST_SECRET_NAME = "test-secret-name"
TEST_SECRET_VALUE_STRING = "test_secret_value"

def setup_function():
    trace_factory.metadata_only = False
    trace_factory.use_single_trace = True
    trace_factory.get_or_create_trace()


def teardown_function():
    trace_factory.singleton_trace = None


def _get_active_trace():
    return trace_factory.active_trace

def _get_secret_binary_value():
    python_version = sys.version_info.major
    if python_version == 2:
        return bytearray(TEST_SECRET_VALUE_STRING)
    return TEST_SECRET_VALUE_STRING.encode()


def _validate_create_secret_metadata(event):
    assert event.resource["operation"] == 'CreateSecret'
    assert event.RESOURCE_TYPE == 'secretsmanager'
    assert event.resource["name"] == TEST_SECRET_NAME


def _validate_get_secret_value_metadata(event):
    assert event.resource["operation"] == 'GetSecretValue'
    assert event.RESOURCE_TYPE == 'secretsmanager'
    assert event.resource["name"] == TEST_SECRET_NAME


def _validate_secret_value_obfuscated(data):
    for key in BotocoreSecretsManagerEvent.SECRET_VALUE_KEYS:
        if key in data:
            assert data[key] == (
                '%s%s' % (TEST_SECRET_VALUE_STRING[0], BotocoreSecretsManagerEvent.OBFUSCATED_DATA)
            )


@mock_secretsmanager
def test_create_secret_string():
    """
    Tests create secret with a secret string
    """
    client = boto3.client('secretsmanager', region_name='us-west-1')
    client.create_secret(Name=TEST_SECRET_NAME, SecretString=TEST_SECRET_VALUE_STRING)
    trace = _get_active_trace()
    event = trace.events[0]
    _validate_create_secret_metadata(event)
    assert 'Parameters' in event.resource['metadata']
    _validate_secret_value_obfuscated(event.resource['metadata']['Parameters'])
    assert 'Response' in event.resource['metadata']
    assert 'ARN' in event.resource['metadata']['Response']


@mock_secretsmanager
def test_create_secret_binary():
    """
    Tests create secret with a secret binary
    """
    client = boto3.client('secretsmanager', region_name='us-west-1')
    client.create_secret(Name=TEST_SECRET_NAME, SecretBinary=_get_secret_binary_value())
    trace = _get_active_trace()
    event = trace.events[0]
    _validate_create_secret_metadata(event)
    assert 'Parameters' in event.resource['metadata']
    _validate_secret_value_obfuscated(event.resource['metadata']['Parameters'])
    assert 'Response' in event.resource['metadata']
    assert 'ARN' in event.resource['metadata']['Response']


@mock_secretsmanager
def test_create_secret_string_metadata_only():
    """
    Tests create secret with a secret string and metadtaonly is set
    """
    trace_factory.metadata_only = True
    client = boto3.client('secretsmanager', region_name='us-west-1')
    client.create_secret(Name=TEST_SECRET_NAME, SecretString=TEST_SECRET_VALUE_STRING)
    trace = _get_active_trace()
    event = trace.events[0]
    _validate_create_secret_metadata(event)
    assert 'Parameters' not in event.resource['metadata']


@mock_secretsmanager
def test_create_secret_binary_metadata_only():
    """
    Tests create secret with a secret binary and metadtaonly is set
    """
    trace_factory.metadata_only = True
    client = boto3.client('secretsmanager', region_name='us-west-1')
    client.create_secret(Name=TEST_SECRET_NAME, SecretBinary=_get_secret_binary_value())
    trace = _get_active_trace()
    event = trace.events[0]
    _validate_create_secret_metadata(event)
    assert 'Parameters' not in event.resource['metadata']


@mock_secretsmanager
def test_get_secret_value_string():
    """
    Tests get secret value and the secret has a string value
    """
    client = boto3.client('secretsmanager', region_name='us-west-1')
    client.create_secret(Name=TEST_SECRET_NAME, SecretString=TEST_SECRET_VALUE_STRING)
    client.get_secret_value(SecretId=TEST_SECRET_NAME)
    trace = _get_active_trace()
    event = trace.events[-1]
    _validate_get_secret_value_metadata(event)
    assert 'Parameters' in event.resource['metadata']
    assert 'SecretId' in event.resource['metadata']['Parameters']
    assert 'Response' in event.resource['metadata']
    _validate_secret_value_obfuscated(event.resource['metadata']['Response'])


@mock_secretsmanager
def test_get_secret_value_binary():
    """
    Tests get secret value and the secret has a binary value
    """
    client = boto3.client('secretsmanager', region_name='us-west-1')
    client.create_secret(Name=TEST_SECRET_NAME, SecretBinary=_get_secret_binary_value())
    client.get_secret_value(SecretId=TEST_SECRET_NAME)
    trace = _get_active_trace()
    event = trace.events[-1]
    _validate_get_secret_value_metadata(event)
    assert 'Parameters' in event.resource['metadata']
    assert 'SecretId' in event.resource['metadata']['Parameters']
    assert 'Response' in event.resource['metadata']
    _validate_secret_value_obfuscated(event.resource['metadata']['Response'])


@mock_secretsmanager
def test_get_secret_value_string_metadata_only():
    """
    Tests get secret value and the secret has string value. metadtaonly is set
    """
    trace_factory.metadata_only = True
    client = boto3.client('secretsmanager', region_name='us-west-1')
    client.create_secret(Name=TEST_SECRET_NAME, SecretString=TEST_SECRET_VALUE_STRING)
    client.get_secret_value(SecretId=TEST_SECRET_NAME)
    trace = _get_active_trace()
    event = trace.events[-1]
    _validate_get_secret_value_metadata(event)
    assert 'Response' not in event.resource['metadata']


@mock_secretsmanager
def test_get_secret_value_binary_metadata_only():
    """
    Tests get secret value and the secret has binary value. metadtaonly is set
    """
    trace_factory.metadata_only = True
    client = boto3.client('secretsmanager', region_name='us-west-1')
    client.create_secret(Name=TEST_SECRET_NAME, SecretBinary=_get_secret_binary_value())
    client.get_secret_value(SecretId=TEST_SECRET_NAME)
    trace = _get_active_trace()
    event = trace.events[-1]
    _validate_get_secret_value_metadata(event)
    assert 'Response' not in event.resource['metadata']


@mock_secretsmanager
def test_get_secret_value_by_arn():
    """
    Tests get secret value using a secret ARN, and the secret has string value. metadtaonly is set
    """
    client = boto3.client('secretsmanager', region_name='us-west-1')
    arn = client.create_secret(Name=TEST_SECRET_NAME, SecretString=TEST_SECRET_VALUE_STRING)["ARN"]
    client.get_secret_value(SecretId=arn)
    trace = _get_active_trace()
    event = trace.events[-1]
    _validate_get_secret_value_metadata(event)
    assert 'Parameters' in event.resource['metadata']
    assert 'SecretId' in event.resource['metadata']['Parameters']
    assert 'Response' in event.resource['metadata']
    _validate_secret_value_obfuscated(event.resource['metadata']['Response'])
