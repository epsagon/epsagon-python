import json
import epsagon.wrappers.python_function
import epsagon.runners.python_function
import epsagon.constants
import mock
from kafka import KafkaProducer

TEST_URL = 'https://example.test/'

def record_mock(*args, **kwargs):
    return [{}, False, False]


@mock.patch('epsagon.trace.TraceFactory.add_event')
@mock.patch('kafka.producer.kafka.KafkaProducer._wait_on_metadata')
@mock.patch('kafka.producer.kafka.KafkaProducer._partition')
@mock.patch('kafka.producer.record_accumulator.RecordAccumulator.append', side_effect=record_mock)
def test_sanity(append_mock, partition_mock, wait_on_metadata_mock, add_event_mock):
    retval = 'success'
    body = {'test': 1}

    @epsagon.wrappers.python_function.python_wrapper
    def wrapped_function():
        producer = KafkaProducer(
            bootstrap_servers=['host:10'],
            client_id='test_client_id',
            api_version=(0, 11, 5),
            value_serializer=lambda x: json.dumps(x).encode('ascii'),
        )
        response = producer.send('topic', body, headers=[('content-encoding', b'base64')])
        return retval
    assert wrapped_function() == retval
    wait_on_metadata_mock.assert_called()
    partition_mock.assert_called()
    append_mock.assert_called()
    add_event_mock.assert_called()
    event = add_event_mock.call_args_list[0].args[0]
    assert event.resource['name'] == 'topic'
    assert event.resource['operation'] == 'send'
    assert event.resource['type'] == 'kafka'
    assert event.resource['metadata']['messaging.kafka.client_id'] == (
        'test_client_id'
    )
    assert event.resource['metadata'][
       'messaging.message_payload_size_bytes'
   ] == len(str(body))
    assert event.resource['metadata']['messaging.message'] == body
    assert (
        epsagon.constants.EPSAGON_HEADER in
        event.resource['metadata']['messaging.headers']
    )


@mock.patch('epsagon.trace.TraceFactory.add_event')
@mock.patch('kafka.producer.kafka.KafkaProducer._wait_on_metadata')
@mock.patch('kafka.producer.kafka.KafkaProducer._partition')
@mock.patch('kafka.producer.record_accumulator.RecordAccumulator.append', side_effect=record_mock)
def test_no_header_injection(append_mock, partition_mock, wait_on_metadata_mock, add_event_mock):
    # Verify header is not injected in older kafka api versions (V1)
    retval = 'success'
    body = {'test': 1}

    @epsagon.wrappers.python_function.python_wrapper
    def wrapped_function():
        producer = KafkaProducer(
            bootstrap_servers=['host:10'],
            client_id='test_client_id',
            api_version=(0, 10, 0),
            value_serializer=lambda x: json.dumps(x).encode('ascii'),
        )
        response = producer.send('topic', body)
        return retval
    assert wrapped_function() == retval
    wait_on_metadata_mock.assert_called()
    partition_mock.assert_called()
    append_mock.assert_called()
    add_event_mock.assert_called()
    event = add_event_mock.call_args_list[0].args[0]
    assert (
        epsagon.constants.EPSAGON_HEADER not in
        event.resource['metadata']
    )
