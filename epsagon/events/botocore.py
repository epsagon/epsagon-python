"""
botocore events module
"""

from __future__ import absolute_import
from ..event import BaseEvent
from botocore.exceptions import ClientError


class BotocoreEvent(BaseEvent):
    """
    Represents base botocore event
    """

    EVENT_MODULE = 'botocore'
    EVENT_TYPE = 'botocore'

    def __init__(self, wrapped, instance, args, kwargs, response, exception):
        super(BotocoreEvent, self).__init__()

        event_operation, _ = args
        self.event_operation = str(event_operation)
        self.resource_name = None

        self.metadata = {
            'region': instance.meta.region_name,
        }

        if response is not None:
            self.update_response(response)

        if exception is not None:
            if isinstance(exception, ClientError):
                self.set_botocore_error(exception)

    def set_botocore_error(self, exception):
        self.set_error()
        self.event_id = exception.response['ResponseMetadata']['RequestId']
        self.metadata['error_message'] = str(exception.message)
        self.metadata['error_code'] = str(exception.response['Error']['Code'])

    def update_response(self, response):
        self.event_id = response['ResponseMetadata']['RequestId']
        self.metadata['retry_attempts'] = response['ResponseMetadata'][
            'RetryAttempts']
        self.metadata['request_id'] = response['ResponseMetadata']['RequestId']
        self.metadata['status_code'] = response['ResponseMetadata'][
            'HTTPStatusCode']


class BotocoreS3Event(BotocoreEvent):
    """
    Represents s3 botocore event
    """

    EVENT_TYPE = 's3'

    def __init__(self, wrapped, instance, args, kwargs, response, exception):
        super(BotocoreS3Event, self).__init__(wrapped, instance, args, kwargs,
                                              response, exception)
        _, request_data = args
        self.resource_name = request_data['Bucket']

        if self.event_operation == 'HeadObject':
            self.metadata['key'] = request_data['Key']
        elif self.event_operation == 'GetObject':
            self.metadata['key'] = request_data['Key']
        elif self.event_operation == 'PutObject':
            self.metadata['key'] = request_data['Key']

    def update_response(self, response):
        super(BotocoreS3Event, self).update_response(response)

        if self.event_operation == 'ListObjects':
            self.metadata['files'] = [
                [str(x['Key']), x['Size'], x['ETag']] for x in
                response['Contents']
            ]
        elif self.event_operation == 'PutObject':
            self.metadata['etag'] = response['ETag']
        elif self.event_operation == 'HeadObject':
            self.metadata['etag'] = response['ETag']
            self.metadata['file_size'] = response['ContentLength']
            self.metadata['last_modified'] = response['LastModified'].strftime(
                '%s')
        elif self.event_operation == 'GetObject':
            self.metadata['etag'] = response['ETag']
            self.metadata['file_size'] = response['ContentLength']
            self.metadata['last_modified'] = response['LastModified'].strftime(
                '%s')


class BotocoreKinesisEvent(BotocoreEvent):
    """
    Represents kinesis botocore event
    """

    EVENT_TYPE = 'kinesis'

    def __init__(self, wrapped, instance, args, kwargs, response, exception):
        super(BotocoreKinesisEvent, self).__init__(wrapped, instance, args,
                                                   kwargs, response,
                                                   exception)
        _, request_data = args
        self.resource_name = request_data['StreamName']

        self.metadata['data'] = request_data['Data']
        self.metadata['partition_key'] = request_data['PartitionKey']

    def update_response(self, response):
        super(BotocoreKinesisEvent, self).update_response(response)

        if self.event_operation == 'PutRecord':
            self.metadata['shard_id'] = response['ShardId']
            self.metadata['sequence_number'] = response['SequenceNumber']


class BotocoreSNSEvent(BotocoreEvent):
    """
    Represents SNS botocore event
    """

    EVENT_TYPE = 'sns'

    def __init__(self, wrapped, instance, args, kwargs, response, exception):
        super(BotocoreSNSEvent, self).__init__(wrapped, instance, args, kwargs,
                                               response, exception)
        _, request_data = args
        self.resource_name = request_data['TopicArn'].split(':')[-1]

        self.metadata['data'] = request_data['Message']

    def update_response(self, response):
        super(BotocoreSNSEvent, self).update_response(response)

        if self.event_operation == 'Publish':
            self.event_id = response['MessageId']
            self.metadata['message_id'] = response['MessageId']


class BotocoreDynamoDBEvent(BotocoreEvent):
    """
    Represents DynamoDB botocore event
    """

    EVENT_TYPE = 'dynamodb'

    def __init__(self, wrapped, instance, args, kwargs, response, exception):
        super(BotocoreDynamoDBEvent, self).__init__(wrapped, instance, args,
                                                    kwargs, response,
                                                    exception)
        _, request_data = args
        self.resource_name = request_data['TableName']

        if self.event_operation == 'PutItem':
            self.metadata['item'] = request_data['Item']
        elif self.event_operation == 'UpdateItem':
            self.metadata['update_params'] = {
                'key': request_data['Key'],
                'expression_attribute_values': request_data.get(
                    'ExpressionAttributeValues', None),
                'update_expression': request_data.get('UpdateExpression', None),
            }
        elif self.event_operation == 'GetItem':
            self.metadata['key'] = request_data['Key']
        elif self.event_operation == 'DeleteItem':
            self.metadata['key'] = request_data['Key']

    def update_response(self, response):
        super(BotocoreDynamoDBEvent, self).update_response(response)

        if self.event_operation == 'Scan':
            self.metadata['items_count'] = response['Count']
            self.metadata['items'] = response['Items']
            self.metadata['scanned_count'] = response['ScannedCount']
        elif self.event_operation == 'GetItem':
            self.metadata['item'] = response['Item']


class BotocoreSESEvent(BotocoreEvent):
    """
    Represents SES botocore event
    """

    EVENT_TYPE = 'ses'

    def __init__(self, wrapped, instance, args, kwargs, response, exception):
        super(BotocoreSESEvent, self).__init__(wrapped, instance, args, kwargs,
                                               response, exception)
        _, request_data = args

        if self.event_operation == 'SendEmail':
            self.metadata['source'] = request_data['Source']
            self.metadata['message'] = request_data['Message']
            self.metadata['destination'] = request_data['Destination']

    def update_response(self, response):
        super(BotocoreSESEvent, self).update_response(response)

        if self.event_operation == 'SendEmail':
            self.metadata['message_id'] = response['MessageId']


class BotocoreLambdaEvent(BotocoreEvent):
    """
    Represents lambda botocore event
    """

    EVENT_TYPE = 'lambda'

    def __init__(self, wrapped, instance, args, kwargs, response, exception):
        super(BotocoreLambdaEvent, self).__init__(wrapped, instance, args,
                                                  kwargs, response,
                                                  exception)
        _, request_data = args

        self.resource_name = request_data['FunctionName']
        self.metadata['payload'] = request_data['Payload']


class BotocoreEventFactory(object):
    @staticmethod
    def create_event(wrapped, instance, args, kwargs, response, exception):
        factory = {
            class_obj.EVENT_TYPE: class_obj
            for class_obj in BotocoreEvent.__subclasses__()
        }

        instance_type = instance.__class__.__name__.lower()
        # getattr(instance, '_service_model').endpoint_prefix

        event_class = factory.get(instance_type, BotocoreEvent)
        event = event_class(wrapped, instance, args, kwargs, response,
                            exception)
        event.add_event()
