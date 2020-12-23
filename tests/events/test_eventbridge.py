from epsagon.trace import trace_factory
from moto import mock_events
import boto3
import json

fake_event = {
    "DetailType": 'test-detail-type',
    "Source": 'test-source',
    "Detail": json.dumps({"test": 1234}),
    "EventBusName": 'test-event-bus-name',
}

fake_event_bus_name_missing = {
    "DetailType": 'test-detail-type',
    "Source": 'test-source',
    "Detail": json.dumps({"test": 1234})
}


def setup_function(func):
    trace_factory.use_single_trace = True
    trace_factory.get_or_create_trace()


def teardown_function(func):
    trace_factory.singleton_trace = None

def _get_active_trace():
    return trace_factory.active_trace


def _put_event(client, event):
    response = client.put_events(Entries=[event])
    return response


@mock_events
def test_event_resources():
    client = boto3.client('events', region_name='us-west-1')
    _put_event(client, fake_event)
    trace = _get_active_trace()
    assert trace.events[0].resource["operation"] == 'PutEvents'
    assert trace.events[0].RESOURCE_TYPE == 'eventbridge'
    assert trace.events[0].resource["name"] == fake_event["EventBusName"]


@mock_events
def test_event_resources_without_bus_name():
    client = boto3.client('events', region_name='us-west-1')
    _put_event(client, fake_event_bus_name_missing)
    trace = _get_active_trace()
    assert trace.events[0].RESOURCE_TYPE == 'eventbridge'
    assert trace.events[0].resource["name"] == 'CloudWatch Events'


@mock_events
def test_event_metadata():
    client = boto3.client('events', region_name='us-west-1')
    _put_event(client, fake_event)
    trace = _get_active_trace()
    assert trace.events[0].resource["metadata"]['aws.cloudwatch.detail_type'] == fake_event["DetailType"]
    assert trace.events[0].resource["metadata"]['aws.cloudwatch.source'] == fake_event["Source"]
    assert trace.events[0].resource["metadata"]['aws.cloudwatch.detail'] == fake_event["Detail"]
