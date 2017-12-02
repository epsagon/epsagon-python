"""
Runner and Triggers for aws_lambda
"""

from __future__ import absolute_import
from uuid import uuid4
from ..event import BaseEvent
from ..trace import tracer
from .. import constants


##########
# runner #
##########

class LambdaRunner(BaseEvent):
    """
    Represents epsagon lambda event (main runner)
    """

    EVENT_MODULE = 'runner'
    EVENT_TYPE = 'lambda'

    def __init__(self, event, context):
        super(LambdaRunner, self).__init__()
        self.resource_name = context.__dict__['function_name']
        self.event_operation = 'invoke'
        self.event_id = context.__dict__['aws_request_id']

        self.metadata = {
            'log_stream_name': context.__dict__['log_stream_name'],
            'log_group_name': context.__dict__['log_group_name'],
            'function_version': context.__dict__['function_version'],
            'cold_start': constants.COLD_START,
            'memory': context.__dict__['memory_limit_in_mb'],
            'region': constants.REGION,
        }

    def set_exception(self, error_code, exception, traceback):
        tracer.error_code = error_code
        self.error_code = error_code
        self.metadata['exception'] = repr(exception)
        self.metadata['traceback'] = traceback

############
# triggers #
############


class BaseLambdaTrigger(BaseEvent):
    """
    Represents base Lambda trigger
    """

    EVENT_MODULE = 'trigger'
    EVENT_TYPE = 'base'

    def __init__(self):
        super(BaseLambdaTrigger, self).__init__()
        self.end_timestamp = self.start_timestamp
        self.event_operation = 'trigger'


class JSONLambdaTrigger(BaseLambdaTrigger):
    """
    Represents JSON simple Lambda trigger
    """

    EVENT_TYPE = 'json'

    def __init__(self, event):
        super(JSONLambdaTrigger, self).__init__()

        self.resource_name = 'trigger'
        self.event_operation = 'Event'
        self.event_id = self.event_id = 'trigger-{}'.format(str(uuid4()))

        self.metadata = {
            'data': event
        }


class S3LambdaTrigger(BaseLambdaTrigger):
    """
    Represents S3 Lambda trigger
    """

    EVENT_TYPE = 's3'

    def __init__(self, event):
        super(S3LambdaTrigger, self).__init__()

        self.resource_name = event['Records'][0]['s3']['bucket']['name']
        self.event_operation = event['Records'][0]['eventName']
        self.event_id = event['Records'][0]['s3']['object']['sequencer']

        self.metadata = {
            'region': event['Records'][0]['awsRegion'],
            'request_parameters': event['Records'][0]['requestParameters'],
            'user_identity': event['Records'][0]['userIdentity'],
            'object_key': event['Records'][0]['s3']['object']['key'],
            'object_size': event['Records'][0]['s3']['object']['size'],
            'object_etag': event['Records'][0]['s3']['object']['eTag'],
        }


class KinesisLambdaTrigger(BaseLambdaTrigger):
    """
    Represents Kinesis Lambda trigger
    """

    EVENT_TYPE = 'kinesis'

    def __init__(self, event):
        super(KinesisLambdaTrigger, self).__init__()

        self.resource_name = event['Records'][0]['eventSourceARN'].split('/')[-1]
        self.event_operation = event['Records'][0]['eventName'].replace('aws:kinesis:', '')
        self.event_id = event['Records'][0]['eventID']

        self.metadata = {
            'region': event['Records'][0]['awsRegion'],
            'invoke_identity': event['Records'][0]['invokeIdentityArn'],
            'sequence_number': event['Records'][0]['kinesis']['sequenceNumber'],
            'partition_key': event['Records'][0]['kinesis']['partitionKey'],
        }


class SNSLambdaTrigger(BaseLambdaTrigger):
    """
    Represents SNS Lambda trigger
    """

    EVENT_TYPE = 'sns'

    def __init__(self, event):
        super(SNSLambdaTrigger, self).__init__()

        self.resource_name = event['Records'][0]['EventSubscriptionArn'].split(':')[-2]
        self.event_operation = str(event['Records'][0]['Sns']['Type'])
        self.event_id = str(event['Records'][0]['Sns']['MessageId'])

        self.metadata = {
            'subject': str(event['Records'][0]['Sns']['Subject']),
            'message': str(event['Records'][0]['Sns']['Message']),
        }


class SNSHTTPTrigger(BaseLambdaTrigger):
    """
    Represents SNS Lambda trigger based on HTTP message
    """

    EVENT_TYPE = 'sns'

    def __init__(self, event):
        super(SNSHTTPTrigger, self).__init__()

        self.resource_name = event['TopicArn'].split(':')[-1]
        self.event_operation = str(event['Type'])
        self.event_id = str(event['MessageId'])

        self.metadata = {
            'message': str(event['Message']),
        }


class APIGatewayLambdaTrigger(BaseLambdaTrigger):
    """
    Represents API Gateway Lambda trigger
    """

    EVENT_TYPE = 'api_gateway'

    def __init__(self, event):
        super(APIGatewayLambdaTrigger, self).__init__()

        self.resource_name = event['resource']
        self.event_operation = event['httpMethod']
        self.event_id = event['requestContext']['requestId']

        self.metadata = {
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

    EVENT_TYPE = 'events'

    def __init__(self, event):
        super(EventsLambdaTrigger, self).__init__()

        self.resource_name = str(event['resources'][0].split('/')[-1])
        self.event_operation = str(event['detail-type'])
        self.event_id = str(event['id'])

        self.metadata = {
            'region': event['region'],
            'detail': None if len(event['detail']) == 0 else event['detail'],
            'account': str(event['account']),
        }


class LambdaTriggerFactory(object):
    @staticmethod
    def factory(event):
        factory = {
            class_obj.EVENT_TYPE: class_obj
            for class_obj in BaseLambdaTrigger.__subclasses__()
        }

        trigger_service = JSONLambdaTrigger.EVENT_TYPE
        if 'Records' in event:
            event_source = 'eventSource'
            if event_source not in event['Records'][0]:
                event_source = 'EventSource'
            trigger_service = event['Records'][0][event_source].split(':')[-1]
        elif 'httpMethod' in event:
            trigger_service = APIGatewayLambdaTrigger.EVENT_TYPE
        elif 'TopicArn' in event:
            return SNSHTTPTrigger(event)
        elif 'source' in event:
            trigger_service = str(event['source'].split('.')[-1])

        return factory.get(trigger_service, JSONLambdaTrigger)(event)
