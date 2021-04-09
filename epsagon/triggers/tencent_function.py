"""
Triggers for Tencent Functions
"""

from __future__ import absolute_import
from uuid import uuid4
from epsagon.utils import add_data_if_needed
from ..event import BaseEvent


class BaseTencentFunctionTrigger(BaseEvent):
    """
    Represents base Tencent Function trigger
    """
    ORIGIN = 'trigger'


class JSONTrigger(BaseTencentFunctionTrigger):
    """
    Represents JSON trigger
    """
    RESOURCE_TYPE = 'json'

    def __init__(self, start_time, event, context, runner):
        """
        Initialize.
        :param start_time: event's start time (epoch)
        :param event: event dict from the entry point
        :param context: the context dict from the entry point
        :param runner: SCF runner event
        """

        super(JSONTrigger, self).__init__(start_time)

        self.event_id = 'trigger-{}'.format(str(uuid4()))

        self.resource['name'] = 'trigger-{}'.format(context['function_name'])
        self.resource['operation'] = self.RESOURCE_TYPE
        self.resource['metadata'] = {}

        add_data_if_needed(
            runner.resource['metadata'],
            'tencent.scf.trigger_data',
            event
        )


class TimerTrigger(BaseTencentFunctionTrigger):
    """
    Represents timer trigger
    """
    RESOURCE_TYPE = 'timer'

    # pylint: disable=W0613
    def __init__(self, start_time, event, context, runner):
        """
        Initialize.
        :param start_time: event's start time (epoch)
        :param event: event dict from the entry point
        :param context: the context dict from the entry point
        :param runner: SCF runner event
        """

        super(TimerTrigger, self).__init__(start_time)

        self.event_id = 'timer-{}'.format(str(uuid4()))
        self.resource['name'] = event['TriggerName']
        self.resource['operation'] = 'Timer'

        self.resource['metadata'] = {
            'tencent.timer.timestamp': event['Time'],
        }

        add_data_if_needed(
            self.resource['metadata'],
            'tencent.timer.message',
            event['Message']
        )


class COSTrigger(BaseTencentFunctionTrigger):
    """
    Represents Cloud Object Storage trigger
    """
    RESOURCE_TYPE = 'cos'

    # pylint: disable=W0613
    def __init__(self, start_time, event, context, runner):
        """
        Initialize.
        :param start_time: event's start time (epoch)
        :param event: event dict from the entry point
        :param context: the context dict from the entry point
        :param runner: SCF runner event
        """

        super(COSTrigger, self).__init__(start_time)
        record = event['Records'][0]
        self.event_id = record['cos']['cosObject']['meta']['x-cos-request-id']
        self.resource['name'] = '{}-{}'.format(
            record['cos']['cosBucket']['name'],
            record['cos']['cosBucket']['appid']
        )
        self.resource['operation'] = record['event']['eventName'].replace(
            'cos:',
            ''
        )

        self.resource['metadata'] = {
            'tencent.region': record['cos']['cosBucket']['cosRegion'],
            'tencent.app_id': record['cos']['cosBucket']['appid'],
            'tencent.cos.object_key': record['cos']['cosObject']['key'],
            'tencent.cos.object_size': record['cos']['cosObject']['size'],
            'tencent.cos.request_id': (
                record['cos']['cosObject']['meta']['x-cos-request-id']
            ),
        }


class CMQTrigger(BaseTencentFunctionTrigger):
    """
    Represents Cloud Message Queue trigger
    """
    RESOURCE_TYPE = 'cmq'

    # pylint: disable=W0613
    def __init__(self, start_time, event, context, runner):
        """
        Initialize.
        :param start_time: event's start time (epoch)
        :param event: event dict from the entry point
        :param context: the context dict from the entry point
        :param runner: SCF runner event
        """

        super(CMQTrigger, self).__init__(start_time)
        record = event['Records'][0]['CMQ']
        self.event_id = record['msgId']
        self.resource['name'] = record['topicName']
        self.resource['operation'] = 'consume'

        self.resource['metadata'] = {
            'tencent.cmq.message.id': record['msgId'],
            'tencent.cmq.message.tags': record['msgTag'],
            'tencent.cmq.request_id': record['requestId'],
            'tencent.cmq.subscription_name': record['subscriptionName'],
        }

        add_data_if_needed(
            self.resource['metadata'],
            'tencent.cmq.message.body',
            record['msgBody']
        )


class KafkaTrigger(BaseTencentFunctionTrigger):
    """
    Represents Kafka trigger
    """
    RESOURCE_TYPE = 'kafka'

    # pylint: disable=W0613
    def __init__(self, start_time, event, context, runner):
        """
        Initialize.
        :param start_time: event's start time (epoch)
        :param event: event dict from the entry point
        :param context: the context dict from the entry point
        :param runner: SCF runner event
        """

        super(KafkaTrigger, self).__init__(start_time)
        record = event['Records'][0]['Ckafka']
        self.event_id = record['msgKey']
        self.resource['name'] = record['topic']
        self.resource['operation'] = 'consume'

        self.resource['metadata'] = {
            'messaging.message.partition': record['partition'],
            'messaging.message.offset': record['offset'],
            'messaging.message.key': record['msgKey'],
        }

        add_data_if_needed(
            self.resource['metadata'],
            'messaging.message.body',
            record['msgBody']
        )


class APIGatewayTrigger(BaseTencentFunctionTrigger):
    """
    Represents API Gateway trigger
    """
    RESOURCE_TYPE = 'http'

    # pylint: disable=W0613
    def __init__(self, start_time, event, context, runner):
        """
        Initialize.
        :param start_time: event's start time (epoch)
        :param event: event dict from the entry point
        :param context: the context dict from the entry point
        :param runner: SCF runner event
        """

        super(APIGatewayTrigger, self).__init__(start_time)
        self.event_id = event['requestContext']['requestId']
        self.resource['name'] = event['headers']['Host']
        self.resource['operation'] = event['httpMethod']

        self.resource['metadata'] = {
            'http.route': event['requestContext']['path'],
            'http.request.path': event['path'],
            'tencent.api_gateway.request_id': (
                event['requestContext']['requestId']
            ),
            'tencent.api_gateway.stage': event['requestContext']['stage'],
        }

        add_data_if_needed(
            self.resource['metadata'],
            'http.request.headers',
            event['headers']
        )

        if event['body']:
            add_data_if_needed(
                self.resource['metadata'],
                'http.request.body',
                event['body']
            )

        if event['pathParameters']:
            add_data_if_needed(
                self.resource['metadata'],
                'http.request.path_params',
                event['pathParameters']
            )

        if event['queryString']:
            add_data_if_needed(
                self.resource['metadata'],
                'http.request.query',
                event['queryString']
            )


class TencentFunctionTriggerFactory(object):
    """
    Represents a Tencent Function Trigger Factory.
    """

    @staticmethod
    def factory(start_time, event, context, runner):
        """
        Creates trigger event object.
        :param start_time: event's start time (epoch)
        :param event: event dict from the entry point
        :param context: the context dict from the entry point
        :param runner: SCF runner event
        :return: Event
        """
        trigger_service = JSONTrigger

        if event.get('Type', None) == 'Timer':
            trigger_service = TimerTrigger
        elif 'httpMethod' in event:
            trigger_service = APIGatewayTrigger
        elif 'Records' in event:
            if 'cos' in event['Records'][0]:
                trigger_service = COSTrigger
            elif 'CMQ' in event['Records'][0]:
                trigger_service = CMQTrigger
            elif 'Ckafka' in event['Records'][0]:
                trigger_service = KafkaTrigger

        return trigger_service(
            start_time,
            event,
            context,
            runner
        )
