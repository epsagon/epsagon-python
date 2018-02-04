"""
botocore events module.
"""

from __future__ import absolute_import
import traceback
from botocore.exceptions import ClientError
from ..trace import tracer
from ..event import BaseEvent


class BotocoreEvent(BaseEvent):
    """
    Represents base botocore event.
    """

    ORIGIN = 'botocore'
    RESOURCE_TYPE = 'botocore'

    def __init__(self, wrapped, instance, args, kwargs, start_time, response,
                 exception):
        """
        Initialize.
        :param wrapped: wrapt's wrapped
        :param instance: wrapt's instance
        :param args: wrapt's args
        :param kwargs: wrapt's kwargs
        :param start_time: Start timestamp (epoch)
        :param response: response data
        :param exception: Exception (if happened)
        """

        super(BotocoreEvent, self).__init__(start_time)

        event_operation, _ = args

        self.resource['operation'] = str(event_operation)
        self.resource['name'] = ''

        self.resource['metadata'] = {
            'region': instance.meta.region_name,
        }

        if response is not None:
            self.update_response(response)

        if exception is not None:
            self.set_exception(exception, traceback.format_exc())

    def set_exception(self, exception, traceback_data):
        """
        Sets exception data on event.
        :param exception: Exception object
        :param traceback_data: traceback string
        :return: None
        """

        super(BotocoreEvent, self).set_exception(exception, traceback_data)

        # Specific handling for botocore errors
        if isinstance(exception, ClientError):
            self.event_id = exception.response['ResponseMetadata']['RequestId']
            botocore_error = exception.response['Error']
            self.resource['metadata']['botocore_error'] = True
            self.resource['metadata']['error_code'] = \
                str(botocore_error.get('Code', ''))
            self.resource['metadata']['error_message'] = \
                str(botocore_error.get('Message', ''))
            self.resource['metadata']['error_type'] = \
                str(botocore_error.get('Type', ''))

    def update_response(self, response):
        """
        Adds response data to event.
        :param response: Response from botocore
        :return: None
        """

        self.event_id = response['ResponseMetadata']['RequestId']
        self.resource['metadata']['retry_attempts'] = \
            response['ResponseMetadata']['RetryAttempts']
        self.resource['metadata']['status_code'] = \
            response['ResponseMetadata']['HTTPStatusCode']


class BotocoreS3Event(BotocoreEvent):
    """
    Represents s3 botocore event.
    """

    RESOURCE_TYPE = 's3'

    def __init__(self, wrapped, instance, args, kwargs, start_time, response,
                 exception):
        """
        Initialize.
        :param wrapped: wrapt's wrapped
        :param instance: wrapt's instance
        :param args: wrapt's args
        :param kwargs: wrapt's kwargs
        :param start_time: Start timestamp (epoch)
        :param response: response data
        :param exception: Exception (if happened)
        """

        super(BotocoreS3Event, self).__init__(
            wrapped,
            instance,
            args,
            kwargs,
            start_time,
            response,
            exception
        )

        _, request_data = args
        self.resource['name'] = request_data['Bucket']

        if self.resource['operation'] in \
                ['HeadObject', 'GetObject', 'PutObject']:
            self.resource['metadata']['key'] = request_data['Key']

    def update_response(self, response):
        """
        Adds response data to event.
        :param response: Response from botocore
        :return: None
        """

        super(BotocoreS3Event, self).update_response(response)

        if self.resource['operation'] == 'ListObjects':
            self.resource['metadata']['files'] = [
                [str(x['Key']), x['Size'], x['ETag']]
                for x in response['Contents']
            ]
        elif self.resource['operation'] == 'PutObject':
            self.resource['metadata']['etag'] = response['ETag']
        elif self.resource['operation'] == 'HeadObject':
            self.resource['metadata']['etag'] = response['ETag']
            self.resource['metadata']['file_size'] = response['ContentLength']
            self.resource['metadata']['last_modified'] = \
                response['LastModified'].strftime('%s')
        elif self.resource['operation'] == 'GetObject':
            self.resource['metadata']['etag'] = response['ETag']
            self.resource['metadata']['file_size'] = response['ContentLength']
            self.resource['metadata']['last_modified'] = \
                response['LastModified'].strftime('%s')


class BotocoreKinesisEvent(BotocoreEvent):
    """
    Represents kinesis botocore event.
    """

    RESOURCE_TYPE = 'kinesis'

    def __init__(self, wrapped, instance, args, kwargs, start_time, response,
                 exception):
        """
        Initialize.
        :param wrapped: wrapt's wrapped
        :param instance: wrapt's instance
        :param args: wrapt's args
        :param kwargs: wrapt's kwargs
        :param start_time: Start timestamp (epoch)
        :param response: response data
        :param exception: Exception (if happened)
        """

        super(BotocoreKinesisEvent, self).__init__(
            wrapped,
            instance,
            args,
            kwargs,
            start_time,
            response,
            exception
        )

        _, request_data = args
        self.resource_name = request_data['StreamName']

        self.resource['metadata']['data'] = request_data['Data']
        self.resource['metadata']['partition_key'] = \
            request_data['PartitionKey']

    def update_response(self, response):
        """
        Adds response data to event.
        :param response: Response from botocore
        :return: None
        """

        super(BotocoreKinesisEvent, self).update_response(response)

        if self.resource['operation'] == 'PutRecord':
            self.resource['metadata']['shard_id'] = response['ShardId']
            self.resource['metadata']['sequence_number'] = \
                response['SequenceNumber']


class BotocoreSNSEvent(BotocoreEvent):
    """
    Represents SNS botocore event.
    """

    RESOURCE_TYPE = 'sns'

    def __init__(self, wrapped, instance, args, kwargs, start_time, response,
                 exception):
        """
        Initialize.
        :param wrapped: wrapt's wrapped
        :param instance: wrapt's instance
        :param args: wrapt's args
        :param kwargs: wrapt's kwargs
        :param start_time: Start timestamp (epoch)
        :param response: response data
        :param exception: Exception (if happened)
        """

        super(BotocoreSNSEvent, self).__init__(
            wrapped,
            instance,
            args,
            kwargs,
            start_time,
            response,
            exception
        )

        _, request_data = args
        self.resource_name = request_data['TopicArn'].split(':')[-1]

        self.resource['metadata']['data'] = request_data['Message']

    def update_response(self, response):
        """
        Adds response data to event.
        :param response: Response from botocore
        :return: None
        """

        super(BotocoreSNSEvent, self).update_response(response)

        if self.resource['operation'] == 'Publish':
            self.resource['metadata']['message_id'] = response['MessageId']


class BotocoreDynamoDBEvent(BotocoreEvent):
    """
    Represents DynamoDB botocore event.
    """

    RESOURCE_TYPE = 'dynamodb'

    def __init__(self, wrapped, instance, args, kwargs, start_time, response,
                 exception):
        """
        Initialize.
        :param wrapped: wrapt's wrapped
        :param instance: wrapt's instance
        :param args: wrapt's args
        :param kwargs: wrapt's kwargs
        :param start_time: Start timestamp (epoch)
        :param response: response data
        :param exception: Exception (if happened)
        """

        super(BotocoreDynamoDBEvent, self).__init__(
            wrapped,
            instance,
            args,
            kwargs,
            start_time,
            response,
            exception
        )

        _, request_data = args
        self.resource_name = request_data['TableName']

        if self.resource['operation'] == 'PutItem':
            self.resource['metadata']['item'] = request_data['Item']
        elif self.resource['operation'] == 'UpdateItem':
            self.resource['metadata']['update_params'] = {
                'key': request_data['Key'],
                'expression_attribute_values': request_data.get(
                    'ExpressionAttributeValues', None),
                'update_expression': request_data.get('UpdateExpression', None),
            }
        elif self.resource['operation'] == 'GetItem':
            self.resource['metadata']['key'] = request_data['Key']
        elif self.resource['operation'] == 'DeleteItem':
            self.resource['metadata']['key'] = request_data['Key']

    def update_response(self, response):
        """
        Adds response data to event.
        :param response: Response from botocore
        :return: None
        """

        super(BotocoreDynamoDBEvent, self).update_response(response)

        if self.resource['operation'] == 'Scan':
            self.resource['metadata']['items_count'] = response['Count']
            self.resource['metadata']['items'] = response['Items']
            self.resource['metadata']['scanned_count'] = \
                response['ScannedCount']
        elif self.resource['operation'] == 'GetItem':
            self.resource['metadata']['item'] = response['Item']


class BotocoreSESEvent(BotocoreEvent):
    """
    Represents SES botocore event.
    """

    RESOURCE_TYPE = 'ses'

    def __init__(self, wrapped, instance, args, kwargs, start_time, response,
                 exception):
        """
        Initialize.
        :param wrapped: wrapt's wrapped
        :param instance: wrapt's instance
        :param args: wrapt's args
        :param kwargs: wrapt's kwargs
        :param start_time: Start timestamp (epoch)
        :param response: response data
        :param exception: Exception (if happened)
        """

        super(BotocoreSESEvent, self).__init__(
            wrapped,
            instance,
            args,
            kwargs,
            start_time,
            response,
            exception
        )

        _, request_data = args

        if self.resource['operation'] == 'SendEmail':
            self.resource['metadata']['source'] = request_data['Source']
            self.resource['metadata']['message'] = request_data['Message']
            self.resource['metadata']['destination'] = \
                request_data['Destination']

    def update_response(self, response):
        """
        Adds response data to event.
        :param response: Response from botocore
        :return: None
        """

        super(BotocoreSESEvent, self).update_response(response)

        if self.resource['operation'] == 'SendEmail':
            self.resource['metadata']['message_id'] = response['MessageId']


class BotocoreLambdaEvent(BotocoreEvent):
    """
    Represents lambda botocore event.
    """

    RESOURCE_TYPE = 'lambda'

    def __init__(self, wrapped, instance, args, kwargs, start_time, response,
                 exception):
        """
        Initialize.
        :param wrapped: wrapt's wrapped
        :param instance: wrapt's instance
        :param args: wrapt's args
        :param kwargs: wrapt's kwargs
        :param start_time: Start timestamp (epoch)
        :param response: response data
        :param exception: Exception (if happened)
        """

        super(BotocoreLambdaEvent, self).__init__(
            wrapped,
            instance,
            args,
            kwargs,
            start_time,
            response,
            exception
        )

        _, request_data = args

        self.resource_name = request_data['FunctionName']
        self.resource['metadata']['payload'] = request_data['Payload']


class BotocoreEventFactory(object):
    """
    Factory class, generates botocore event.
    """

    FACTORY = {
        class_obj.RESOURCE_TYPE: class_obj
        for class_obj in BotocoreEvent.__subclasses__()
    }

    @staticmethod
    def create_event(wrapped, instance, args, kwargs, start_time, response,
                     exception):
        instance_type = instance.__class__.__name__.lower()
        event_class = BotocoreEventFactory.FACTORY.get(
            instance_type,
            BotocoreEvent
        )
        event = event_class(
            wrapped,
            instance,
            args,
            kwargs,
            start_time,
            response,
            exception
        )
        tracer.add_event(event)
