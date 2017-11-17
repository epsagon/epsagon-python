import json
import os
import epsagon
from epsagon import constants
from epsagon import trace

# coverage run --source epsagon -m py.test tests


class Context(object):
    def __init__(self, context):
        self.__dict__ = context


def load_context(context_name='base'):
    context = None
    with open(os.path.join('tests', 'contexts', '{}.json'.format(context_name))) as context_file:
        context = Context(json.loads(context_file.read()))
    return context


def load_event(event_name):
    event = None
    with open(os.path.join('tests', 'events', '{}.json'.format(event_name))) as event_file:
        event = json.loads(event_file.read())
    return event


def test_cold_start_value():
    reload(epsagon.constants)
    epsagon.init('test')
    assert constants.COLD_START

    event = load_event('api_gateway')
    context = load_context()
    demo(event, context)
    assert not constants.COLD_START


def test_region_detection():
    new_region = 'us-east-1'
    os.environ['AWS_REGION'] = new_region
    reload(epsagon.constants)
    assert constants.REGION == new_region


def test_initialization_token_assert():
    reload(epsagon.trace)
    reload(epsagon.wrapper)

    event = load_event('api_gateway')
    context = load_context()
    try:
        demo(event, context)
        assert False
    except AssertionError:
        pass


def test_token_and_appname_initialization():
    reload(epsagon.trace)
    reload(epsagon.wrapper)

    epsagon.init('test', 'test')
    event = load_event('api_gateway')
    context = load_context()
    demo(event, context)
    assert epsagon.trace.tracer.token == 'test'
    assert epsagon.trace.tracer.app_name == 'test'


@epsagon.lambda_wrapper
def demo(event, context):
    pass