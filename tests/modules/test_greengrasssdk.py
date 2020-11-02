import mock
from epsagon.events.greengrasssdk import GreengrassEventFactory


@mock.patch('epsagon.trace.TraceFactory.add_event')
def test_sanity(add_event_mock):
    params = {
        'topic': 'name',
        'queueFullPolicy': True,
        'payload': 'test',
    }
    GreengrassEventFactory.create_event(None, None, None, params, None, None, None)
    add_event_mock.assert_called_once()
    event = add_event_mock.call_args_list[0].args[0]
    assert event.event_id.startswith('greengrass-')
    assert event.resource['name'] == 'name'
    assert event.resource['operation'] == 'publish'
    assert event.resource['metadata']['aws.greengrass.queueFullPolicy'] == True
    assert event.resource['metadata']['aws.greengrass.payload'] == 'test'
