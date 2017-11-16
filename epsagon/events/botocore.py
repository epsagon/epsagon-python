"""
botocore events module
"""
from __future__ import absolute_import
from ..common import ErrorCode
from ..trace import tracer
from ..event import BaseEvent


class BotocoreEvent(BaseEvent):
    """
    Represents base botocore event
    """

    EVENT_MODULE = 'botocore'
    EVENT_TYPE = 'botocore'

    def __init__(self, instance, args):
        super(BotocoreEvent, self).__init__()

        event_operation, _ = args
        self.event_operation = str(event_operation)
        self.resource_name = None

        self.metadata = {
            'region': instance.meta.region_name,
        }

    def set_error(self, exception):
        self.event_id = exception.response['ResponseMetadata']['RequestId']
        tracer.error_code = ErrorCode.ERROR
        self.error_code = ErrorCode.ERROR
        self.metadata['error_message'] = str(exception.message)
        self.metadata['error_code'] = str(exception.response['Error']['Code'])

    def post_update(self, parsed_response):
        self.event_id = parsed_response['ResponseMetadata']['RequestId']
        self.metadata['retry_attempts'] = parsed_response['ResponseMetadata']['RetryAttempts']
        self.metadata['request_id'] = parsed_response['ResponseMetadata']['RequestId']
        self.metadata['status_code'] = parsed_response['ResponseMetadata']['HTTPStatusCode']


class BotocoreS3Event(BotocoreEvent):
    """
    Represents s3 botocore event
    """

    EVENT_TYPE = 's3'

    def __init__(self, instance, args):
        super(BotocoreS3Event, self).__init__(instance, args)
        _, request_data = args
        self.resource_name = request_data['Bucket']

    def post_update(self, parsed_response):
        super(BotocoreS3Event, self).post_update(parsed_response)

        if self.event_operation == 'ListObjects':
            self.metadata['files'] = [
                [str(x['Key']), x['Size'], x['ETag']] for x in parsed_response['Contents']
            ]
        elif self.event_operation == 'PutObject':
            self.metadata['etag'] = parsed_response['ETag']


class BotocoreKinesisEvent(BotocoreEvent):
    """
    Represents kinesis botocore event
    """

    EVENT_TYPE = 'kinesis'

    def __init__(self, instance, args):
        super(BotocoreKinesisEvent, self).__init__(instance, args)
        _, request_data = args
        self.resource_name = request_data['StreamName']

        self.metadata['data'] = request_data['Data']
        self.metadata['partition_key'] = request_data['PartitionKey']

    def post_update(self, parsed_response):
        super(BotocoreKinesisEvent, self).post_update(parsed_response)

        if self.event_operation == 'PutRecord':
            self.metadata['shard_id'] = parsed_response['ShardId']
            self.metadata['sequence_number'] = parsed_response['SequenceNumber']


class BotocoreSNSEvent(BotocoreEvent):
    """
    Represents SNS botocore event
    """

    EVENT_TYPE = 'sns'

    def __init__(self, instance, args):
        super(BotocoreSNSEvent, self).__init__(instance, args)
        _, request_data = args
        self.resource_name = request_data['TopicArn'].split(':')[-1]

        self.metadata['data'] = request_data['Message']

    def post_update(self, parsed_response):
        super(BotocoreSNSEvent, self).post_update(parsed_response)

        if self.event_operation == 'Publish':
            self.event_id = parsed_response['MessageId']
            self.metadata['message_id'] = parsed_response['MessageId']


class BotocoreDynamoDBEvent(BotocoreEvent):
    """
    Represents DynamoDB botocore event
    """

    EVENT_TYPE = 'dynamodb'

    def __init__(self, instance, args):
        super(BotocoreDynamoDBEvent, self).__init__(instance, args)
        _, request_data = args
        self.resource_name = request_data['TableName']

        if self.event_operation == 'PutItem':
            self.metadata['item'] = request_data['Item']
        elif self.event_operation == 'UpdateItem':
            self.metadata['update_params'] = {
                'key': request_data['Key'],
                'expression_attribute_values': request_data['ExpressionAttributeValues'],
                'update_expression': request_data['UpdateExpression'],
            }

    def post_update(self, parsed_response):
        super(BotocoreDynamoDBEvent, self).post_update(parsed_response)

        if self.event_operation == 'Scan':
            self.metadata['items_count'] = parsed_response['Count']
            self.metadata['items'] = parsed_response['Items']
            self.metadata['scanned_count'] = parsed_response['ScannedCount']


class BotocoreLambdaEvent(BotocoreEvent):
    """
    Represents lambda botocore event
    """

    EVENT_TYPE = 'lambda'

    def __init__(self, instance, args):
        super(BotocoreLambdaEvent, self).__init__(instance, args)
        _, request_data = args

        self.resource_name = request_data['FunctionName']
        self.metadata['payload'] = request_data['Payload']


class BotocoreEventFactory(object):
    @staticmethod
    def factory(instance, args):
        factory = {
            class_obj.EVENT_TYPE: class_obj
            for class_obj in BotocoreEvent.__subclasses__()
        }

        instance_type = getattr(instance, '_service_model').endpoint_prefix

        return factory.get(instance_type, BotocoreEvent)(instance, args)
