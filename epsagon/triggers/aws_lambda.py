"""
Triggers for aws_lambda
"""

from __future__ import absolute_import
from uuid import uuid4
from importlib import import_module
import hashlib
import json
from epsagon.utils import add_data_if_needed, parse_json, print_debug
from ..event import BaseEvent
from ..constants import EPSAGON_HEADER

# Conditionally importing boto3
TypeDeserializer = None  # pylint: disable=invalid-name
try:
    TypeDeserializer = (  # pylint: disable=invalid-name
        import_module('boto3.dynamodb.types').TypeDeserializer
    )
except ImportError:
    pass


class BaseLambdaTrigger(BaseEvent):
    """
    Represents base Lambda trigger
    """
    ORIGIN = 'trigger'


class JSONLambdaTrigger(BaseLambdaTrigger):
    """
    Represents JSON simple Lambda trigger
    """
    RESOURCE_TYPE = 'json'

    def __init__(self, start_time, event, context):
        """
        Initialize.
        :param start_time: event's start time (epoch)
        :param event: event dict from the entry point
        :param context: the context dict from the entry point
        """

        super(JSONLambdaTrigger, self).__init__(start_time)

        self.event_id = 'trigger-{}'.format(str(uuid4()))

        self.resource['name'] = 'trigger-{}'.format(context.function_name)
        self.resource['operation'] = self.RESOURCE_TYPE
        self.resource['metadata'] = {}

        add_data_if_needed(self.resource['metadata'], 'data', event)


class S3LambdaTrigger(BaseLambdaTrigger):
    """
    Represents S3 Lambda trigger
    """
    RESOURCE_TYPE = 's3'

    # pylint: disable=W0613
    def __init__(self, start_time, event, context):
        """
        Initialize.
        :param start_time: event's start time (epoch)
        :param event: event dict from the entry point
        :param context: the context dict from the entry point
        """

        super(S3LambdaTrigger, self).__init__(start_time)

        self.event_id = 's3-trigger-{0}'.format(
            event['Records'][0]['responseElements']['x-amz-request-id']
        )
        self.resource['name'] = event['Records'][0]['s3']['bucket']['name']
        self.resource['operation'] = event['Records'][0]['eventName']

        self.resource['metadata'] = {
            'region': event['Records'][0]['awsRegion'],
            'request_parameters': event['Records'][0]['requestParameters'],
            'user_identity': event['Records'][0]['userIdentity'],
            'object_key': event['Records'][0]['s3']['object']['key'],
            'object_size': event['Records'][0]['s3']['object']['size'],
            'object_etag': event['Records'][0]['s3']['object'].get('eTag', ''),
            'object_sequencer': event['Records'][0]['s3']['object'][
                'sequencer'
            ],
            'x-amz-request-id': event['Records'][0]['responseElements'][
                'x-amz-request-id'
            ],
        }


class DynamoDBLambdaTrigger(BaseLambdaTrigger):
    """
    Represents DynamoDB Lambda trigger
    """
    RESOURCE_TYPE = 'dynamodb'

    # pylint: disable=W0613
    def __init__(self, start_time, event, context):
        """
        Initialize.
        :param start_time: event's start time (epoch)
        :param event: event dict from the entry point
        :param context: the context dict from the entry point
        """

        super(DynamoDBLambdaTrigger, self).__init__(start_time)
        self.deserializer = TypeDeserializer() if TypeDeserializer else None

        record = event['Records'][0]
        self.event_id = record['eventID']
        self.resource['name'] = record['eventSourceARN'].split('/')[-3]
        self.resource['operation'] = record['eventName']

        if record['eventName'] == 'REMOVE':
            deserialized_item = self._deserialize_item(
                record['dynamodb']['Keys']
            )
        elif record['eventName'] == 'MODIFY':
            deserialized_item = self._deserialize_item(
                record['dynamodb']['Keys']
            )
        else:
            item = record['dynamodb']['NewImage']
            deserialized_item = self._deserialize_item(item)
            add_data_if_needed(self.resource['metadata'], 'New Image', item)

        self.resource['metadata'] = {
            'region': record['awsRegion'],
            'sequence_number': record['dynamodb']['SequenceNumber'],
        }

        if deserialized_item is not None:
            self.resource['metadata']['item_hash'] = hashlib.md5(
                json.dumps(deserialized_item, sort_keys=True).encode('utf-8')
            ).hexdigest()

    def _deserialize_item(self, item):
        """
        Deserialize DynamoDB Item in order to remove types definitions.
        :param item: The item to deserialize.
        :return: Deserialized item.
        """
        if self.deserializer is None:
            return None
        deserialized_item = item.copy()
        for key in item:
            try:
                deserialized_item[key] = self.deserializer.deserialize(
                    item[key]
                )
            except (TypeError, AttributeError):
                break
        return deserialized_item


class KinesisLambdaTrigger(BaseLambdaTrigger):
    """
    Represents Kinesis Lambda trigger
    """
    RESOURCE_TYPE = 'kinesis'

    # pylint: disable=W0613
    def __init__(self, start_time, event, context):
        """
        Initialize.
        :param start_time: event's start time (epoch)
        :param event: event dict from the entry point
        :param context: the context dict from the entry point
        """

        super(KinesisLambdaTrigger, self).__init__(start_time)

        self.event_id = event['Records'][0]['eventID']
        self.resource['name'] = \
            event['Records'][0]['eventSourceARN'].split('/')[-1]
        self.resource['operation'] = \
            event['Records'][0]['eventName'].replace('aws:kinesis:', '')

        self.resource['metadata'] = {
            'region': event['Records'][0]['awsRegion'],
            'invoke_identity': event['Records'][0]['invokeIdentityArn'],
            'sequence_number': event['Records'][0]['kinesis']['sequenceNumber'],
            'partition_key': event['Records'][0]['kinesis']['partitionKey'],
            'record_count': len(event['Records'])
        }


class SNSLambdaTrigger(BaseLambdaTrigger):
    """
    Represents SNS Lambda trigger
    """
    RESOURCE_TYPE = 'sns'

    # pylint: disable=W0613
    def __init__(self, start_time, event, context):
        """
        Initialize.
        :param start_time: event's start time (epoch)
        :param event: event dict from the entry point
        :param context: the context dict from the entry point
        """

        super(SNSLambdaTrigger, self).__init__(start_time)

        self.event_id = str(event['Records'][0]['Sns']['MessageId'])
        self.resource['name'] = \
            event['Records'][0]['EventSubscriptionArn'].split(':')[-2]
        self.resource['operation'] = str(event['Records'][0]['Sns']['Type'])

        self.resource['metadata'] = {
            'Notification Subject': str(event['Records'][0]['Sns']['Subject'])
        }
        message = str(event['Records'][0]['Sns']['Message'])
        add_data_if_needed(
            self.resource['metadata'],
            'Notification Message',
            message
        )
        print_debug('Initialized SNS Lambda trigger')


class SQSLambdaTrigger(BaseLambdaTrigger):
    """
    Represents SQS Lambda trigger.
    """
    RESOURCE_TYPE = 'sqs'

    # pylint: disable=W0613
    def __init__(self, start_time, event, context):
        """
        Initialize.
        :param start_time: event's start time (epoch).
        :param event: event dict from the entry point.
        :param context: the context dict from the entry point.
        """

        super(SQSLambdaTrigger, self).__init__(start_time)

        record = event['Records'][0]
        self.event_id = record['messageId']
        self.resource['name'] = record['eventSourceARN'].split(':')[-1]
        self.resource['operation'] = 'ReceiveMessage'

        self.resource['metadata'] = {
            'MD5 Of Message Body': record['md5OfBody'],
            'Sender ID': record['attributes']['SenderId'],
            'Approximate Receive Count': record['attributes'][
                'ApproximateReceiveCount'
            ],
            'Sent Timestamp': record['attributes']['SentTimestamp'],
            'Approximate First Receive Timestamp': record['attributes'][
                'ApproximateFirstReceiveTimestamp'
            ],
        }
        sqs_message_body = record['body']

        self.resource['metadata']['Number Of Messages'] = len(event['Records'])

        add_data_if_needed(
            self.resource['metadata'],
            'Message Body',
            str(sqs_message_body)
        )

        message_body = parse_json(sqs_message_body)
        if not message_body:
            return
        message_body_input = message_body.get('input')
        if not message_body_input:
            return
        if isinstance(message_body_input, dict):
            steps_dict = message_body_input.get('Epsagon')
            if not steps_dict:
                return
            self.resource['metadata'] = {'steps_dict': steps_dict}


class ProxyAPIGatewayLambdaTrigger(BaseLambdaTrigger):
    """
    Represents a Proxy API Gateway Lambda trigger.
    """
    RESOURCE_TYPE = 'api_gateway'

    # pylint: disable=W0613
    def __init__(self, start_time, event, context):
        """
        Initialize.
        :param start_time: event's start time (epoch)
        :param event: event dict from the entry point
        :param context: the context dict from the entry point
        """

        super(ProxyAPIGatewayLambdaTrigger, self).__init__(start_time)
        default_request_context = {
            'requestId': str(uuid4()),
            'apiId': 'N/A',
            'stage': event.get('environment', 'N/A')
        }
        request_context = event.get('requestContext', default_request_context)
        self.event_id = request_context['requestId']
        self.resource['name'] = event['headers'].get(
            'Host',
            request_context.get('apiId')
        )

        self.resource['operation'] = event['httpMethod']

        query_params = event.get(
            'queryStringParameters',
            event.get('queryParams', 'N/A')
        )
        path_params = event.get(
            'pathParameters',
            event.get('pathParams', 'N/A')
        )

        self.resource['metadata'] = {
            'stage': request_context.get('stage', 'N/A'),
            'query_string_parameters': query_params,
            'path_parameters': path_params,
            'path': event.get('resource', 'N/A'),
        }

        add_data_if_needed(self.resource['metadata'], 'body', event['body'])
        add_data_if_needed(
            self.resource['metadata'],
            'headers',
            event['headers']
        )


class NoProxyAPIGatewayLambdaTrigger(BaseLambdaTrigger):
    """
    Represents an API Gateway Lambda trigger that uses the API Gateway method
    request passthrough template.
    """
    RESOURCE_TYPE = 'api_gateway_no_proxy'

    # pylint: disable=W0613
    def __init__(self, start_time, event, context):
        """
        Initialize.
        :param start_time: event's start time (epoch)
        :param event: event dict from the entry point
        :param context: the context dict from the entry point
        """

        super(NoProxyAPIGatewayLambdaTrigger, self).__init__(start_time)

        self.event_id = event['context']['request-id']
        self.resource['name'] = event['params']['header'].get(
            'Host',
            event['context']['api-id']
        )
        self.resource['operation'] = event['context']['http-method']

        self.resource['metadata'] = {
            'stage': event['context']['stage'],
            'query_string_parameters': event['params']['querystring'],
            'path_parameters': event['params']['path'],
            'path': event['context']['resource-path'],
        }

        add_data_if_needed(
            self.resource['metadata'],
            'body',
            event['body-json']
        )
        add_data_if_needed(
            self.resource['metadata'],
            'headers',
            event['params']['header']
        )


class ElasticLoadBalancerLambdaTrigger(BaseLambdaTrigger):
    """
    Represents an Elastic Load Balancer trigger.
    """
    RESOURCE_TYPE = 'elastic_load_balancer'

    # pylint: disable=W0613
    def __init__(self, start_time, event, context):
        """
        Initialize.
        :param start_time: event's start time (epoch)
        :param event: event dict from the entry point
        :param context: the context dict from the entry point
        """
        super(ElasticLoadBalancerLambdaTrigger, self).__init__(start_time)

        self.event_id = 'elb-{}'.format(str(uuid4()))
        self.resource['name'] = event['headers']['host']
        self.resource['operation'] = event['httpMethod']

        epsagon_trace_id = event['headers'].get(EPSAGON_HEADER)
        self.resource['metadata'] = {
            'http_trace_id': epsagon_trace_id,
            'query_string_parameters': event['queryStringParameters'],
            'target_group_arn': (
                event['requestContext']['elb']['targetGroupArn']
            ),
            'path': event['path']
        }

        if epsagon_trace_id:
            self.resource['metadata']['http_trace_id'] = epsagon_trace_id

        add_data_if_needed(
            self.resource['metadata'],
            'body',
            event['body']
        )
        add_data_if_needed(
            self.resource['metadata'],
            'headers',
            event['headers']
        )


class EventsLambdaTrigger(BaseLambdaTrigger):
    """
    Represents Events (schedule) Lambda trigger
    """
    RESOURCE_TYPE = 'events'

    # pylint: disable=W0613
    def __init__(self, start_time, event, context):
        """
        Initialize.
        :param start_time: event's start time (epoch)
        :param event: event dict from the entry point
        :param context: the context dict from the entry point
        """

        super(EventsLambdaTrigger, self).__init__(start_time)

        self.event_id = str(event['id'])
        name = 'CloudWatch Events'
        if event['resources'] and isinstance(event['resources'][0], str):
            name = str(event['resources'][0].split('/')[-1])
        self.resource['name'] = name
        self.resource['operation'] = str(event['detail-type'])

        self.resource['metadata'] = {
            'region': event['region'],
            'detail': None if not event['detail'] else event['detail'],
            'account': str(event['account']),
        }


class LambdaTriggerFactory(object):
    """
    Represents a Lambda Trigger Factory.
    """
    FACTORY = {
        class_obj.RESOURCE_TYPE: class_obj
        for class_obj in BaseLambdaTrigger.__subclasses__()
    }

    @staticmethod
    def factory(start_time, event, context):
        """
        Creates trigger event object.
        :param start_time: event's start time (epoch)
        :param event: event dict from the entry point
        :param context: the context dict from the entry point
        :return: Event
        """
        trigger_service = JSONLambdaTrigger.RESOURCE_TYPE
        if 'Records' in event:
            event_source = 'eventSource'
            if event_source not in event['Records'][0]:
                event_source = 'EventSource'
            trigger_service = event['Records'][0][event_source].split(':')[-1]
        elif 'requestContext' in event and 'elb' in event['requestContext']:
            trigger_service = ElasticLoadBalancerLambdaTrigger.RESOURCE_TYPE
        elif 'httpMethod' in event:
            trigger_service = ProxyAPIGatewayLambdaTrigger.RESOURCE_TYPE
        elif 'context' in event and 'http-method' in event['context']:
            trigger_service = NoProxyAPIGatewayLambdaTrigger.RESOURCE_TYPE
        elif 'source' in event and 'detail-type' in event and 'detail' in event:
            trigger_service = EventsLambdaTrigger.RESOURCE_TYPE
        elif 'source' in event:
            trigger_service = str(event['source'].split('.')[-1])
        return LambdaTriggerFactory.FACTORY.get(trigger_service)(
            start_time,
            event,
            context
        )
