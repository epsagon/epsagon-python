"""
Runner and Triggers for aws_lambda
"""

from __future__ import absolute_import
from ..event import BaseEvent
from ..trace import tracer


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
        }

    def set_error(self, error_code, exception, traceback):
        tracer.error_code = error_code
        self.error_code = error_code
        self.metadata['exception'] = exception
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


class S3LambdaTrigger(BaseLambdaTrigger):
    """
    Represents S3 Lambda trigger
    """

    EVENT_TYPE = 's3'

    def __init__(self, event):
        super(S3LambdaTrigger, self).__init__()
        self.end_timestamp = self.start_timestamp

        # TODO: Need to support multiple records

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
        self.end_timestamp = self.start_timestamp

        # TODO: Need to support multiple records

        self.resource_name = event['Records'][0]['eventSourceARN'].split('/')[-1]
        self.event_operation = event['Records'][0]['eventName'].replace('aws:kinesis:', '')
        self.event_id = event['Records'][0]['eventID']

        self.metadata = {
            'region': event['Records'][0]['awsRegion'],
            'invoke_identity': event['Records'][0]['invokeIdentityArn'],
            'sequence_number': event['Records'][0]['kinesis']['partitionKey'],
            'partition_key': event['Records'][0]['kinesis']['sequenceNumber'],
        }


class APIGatewayLambdaTrigger(BaseLambdaTrigger):
    """
    Represents API Gateway Lambda trigger
    """

    EVENT_TYPE = 'api_gateway'

    def __init__(self, event):
        super(APIGatewayLambdaTrigger, self).__init__()
        self.end_timestamp = self.start_timestamp

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


class LambdaTriggerFactory(object):

    FACTORY_DICT = {
        S3LambdaTrigger.EVENT_TYPE: S3LambdaTrigger,
        KinesisLambdaTrigger.EVENT_TYPE: KinesisLambdaTrigger,
        APIGatewayLambdaTrigger.EVENT_TYPE: APIGatewayLambdaTrigger,
    }

    @staticmethod
    def factory(event):
        trigger_service = None
        if 'Records' in event:
            trigger_service = event['Records'][0]['eventSource'].split(':')[-1]
        elif 'httpMethod' in event:
            trigger_service = APIGatewayLambdaTrigger.EVENT_TYPE

        if trigger_service not in LambdaTriggerFactory.FACTORY_DICT:
            return None

        return LambdaTriggerFactory.FACTORY_DICT[trigger_service](event)
