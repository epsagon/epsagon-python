"""
Triggers for aws_lambda
"""

from __future__ import absolute_import
import simplejson as json
import hashlib
from uuid import uuid4

from boto3.dynamodb.types import TypeDeserializer

from ..event import BaseEvent


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

    def __init__(self, start_time, event):
        """
        Initialize.
        :param start_time: event's start time (epoch)
        :param event: event dict from the entry point
        """

        super(JSONLambdaTrigger, self).__init__(start_time)

        self.event_id = 'trigger-{}'.format(str(uuid4()))

        self.resource['name'] = self.RESOURCE_TYPE
        self.resource['operation'] = self.RESOURCE_TYPE
        self.resource['metadata'] = {
            'data': event
        }


class S3LambdaTrigger(BaseLambdaTrigger):
    """
    Represents S3 Lambda trigger
    """
    RESOURCE_TYPE = 's3'

    def __init__(self, start_time, event):
        """
        Initialize.
        :param start_time: event's start time (epoch)
        :param event: event dict from the entry point
        """

        super(S3LambdaTrigger, self).__init__(start_time)

        self.event_id = event['Records'][0]['s3']['object']['sequencer']
        self.resource['name'] = event['Records'][0]['s3']['bucket']['name']
        self.resource['operation'] = event['Records'][0]['eventName']

        self.resource['metadata'] = {
            'region': event['Records'][0]['awsRegion'],
            'request_parameters': event['Records'][0]['requestParameters'],
            'user_identity': event['Records'][0]['userIdentity'],
            'object_key': event['Records'][0]['s3']['object']['key'],
            'object_size': event['Records'][0]['s3']['object']['size'],
            'object_etag': event['Records'][0]['s3']['object']['eTag'],
        }


class DynamoDBLambdaTrigger(BaseLambdaTrigger):
    """
    Represents S3 Lambda trigger
    """
    RESOURCE_TYPE = 'dynamodb'

    def __init__(self, start_time, event):
        """
        Initialize.
        :param start_time: event's start time (epoch)
        :param event: event dict from the entry point
        """
        super(DynamoDBLambdaTrigger, self).__init__(start_time)
        record = event['Records'][0]
        self.event_id = record['eventID']
        self.resource['name'] = record['eventSourceARN'].split('/')[-3]
        self.resource['operation'] = record['eventName']
        item = record['dynamodb']['NewImage']

        # Deserialize the data in order to remove dynamoDB data types.
        deser = TypeDeserializer()
        des_item = item.copy()
        for key in item:
            des_item[key] = deser.deserialize(item[key])
        self.resource['metadata']['item_hash'] = hashlib.md5(
            json.dumps(des_item, sort_keys=True)).hexdigest()

        self.resource['metadata'] = {
            'region': record['awsRegion'],
            'sequence_number': record['dynamodb']['SequenceNumber'],
            'item_hash': hashlib.md5(
                json.dumps(des_item, sort_keys=True)
            ).hexdigest()
        }


class KinesisLambdaTrigger(BaseLambdaTrigger):
    """
    Represents Kinesis Lambda trigger
    """
    RESOURCE_TYPE = 'kinesis'

    def __init__(self, start_time, event):
        """
        Initialize.
        :param start_time: event's start time (epoch)
        :param event: event dict from the entry point
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
        }


class SNSLambdaTrigger(BaseLambdaTrigger):
    """
    Represents SNS Lambda trigger
    """
    RESOURCE_TYPE = 'sns'

    def __init__(self, start_time, event):
        """
        Initialize.
        :param start_time: event's start time (epoch)
        :param event: event dict from the entry point
        """

        super(SNSLambdaTrigger, self).__init__(start_time)

        self.event_id = str(event['Records'][0]['Sns']['MessageId'])
        self.resource['name'] = \
            event['Records'][0]['EventSubscriptionArn'].split(':')[-2]
        self.resource['operation'] = str(event['Records'][0]['Sns']['Type'])

        self.resource['metadata'] = {
            'Notification Subject': str(event['Records'][0]['Sns']['Subject']),
            'Notification Message': str(event['Records'][0]['Sns']['Message']),
        }


class APIGatewayLambdaTrigger(BaseLambdaTrigger):
    """
    Represents API Gateway Lambda trigger
    """
    RESOURCE_TYPE = 'api_gateway'

    def __init__(self, start_time, event):
        """
        Initialize.
        :param start_time: event's start time (epoch)
        :param event: event dict from the entry point
        """

        super(APIGatewayLambdaTrigger, self).__init__(start_time)

        self.event_id = event['requestContext']['requestId']
        self.resource['name'] = event['resource']
        self.resource['operation'] = event['httpMethod']

        self.resource['metadata'] = {
            'stage': event['requestContext']['stage'],
            'body': event['body'],
            'headers': event['headers'],
            'query_string_parameters': event['queryStringParameters'],
            'path_parameters': event['pathParameters'],
        }


class EventsLambdaTrigger(BaseLambdaTrigger):
    """
    Represents Events (schedule) Lambda trigger
    """
    RESOURCE_TYPE = 'events'

    def __init__(self, start_time, event):
        """
        Initialize.
        :param start_time: event's start time (epoch)
        :param event: event dict from the entry point
        """

        super(EventsLambdaTrigger, self).__init__(start_time)

        self.event_id = str(event['id'])
        self.resource['name'] = str(event['resources'][0].split('/')[-1])
        self.resource['operation'] = str(event['detail-type'])

        self.resource['metadata'] = {
            'region': event['region'],
            'detail': None if len(event['detail']) == 0 else event['detail'],
            'account': str(event['account']),
        }


class LambdaTriggerFactory(object):
    FACTORY = {
        class_obj.RESOURCE_TYPE: class_obj
        for class_obj in BaseLambdaTrigger.__subclasses__()
    }

    @staticmethod
    def factory(start_time, event):
        """
        Creates trigger event object.
        :param start_time: event's start time (epoch)
        :param event: event dict from the entry point
        :return: Event
        """
        trigger_service = JSONLambdaTrigger.RESOURCE_TYPE
        if 'Records' in event:
            event_source = 'eventSource'
            if event_source not in event['Records'][0]:
                event_source = 'EventSource'
            trigger_service = event['Records'][0][event_source].split(':')[-1]
        elif 'httpMethod' in event:
            trigger_service = APIGatewayLambdaTrigger.RESOURCE_TYPE
        elif 'source' in event:
            trigger_service = str(event['source'].split('.')[-1])

        return LambdaTriggerFactory.FACTORY.get(
            trigger_service,
            JSONLambdaTrigger
        )(start_time, event)
