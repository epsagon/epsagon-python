"""
botocore events module.
"""

from __future__ import absolute_import

import hashlib
import traceback
import simplejson as json
from boto3.dynamodb.types import TypeDeserializer
from botocore.exceptions import ClientError
from ..trace import tracer
from ..event import BaseEvent


def empty_func():
    return


class BotocoreEvent(BaseEvent):
    """
    Represents base botocore event.
    """

    ORIGIN = 'botocore'
    RESOURCE_TYPE = 'botocore'
    RESPONSE_TO_FUNC = {}
    OPERATION_TO_FUNC = {}

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
                [str(x['Key']).strip('"'), x['Size'], x['ETag']]
                for x in response['Contents']
            ]
        elif self.resource['operation'] == 'PutObject':
            self.resource['metadata']['etag'] = response['ETag'].strip('"')
        elif self.resource['operation'] == 'HeadObject':
            self.resource['metadata']['etag'] = response['ETag'].strip('"')
            self.resource['metadata']['file_size'] = response['ContentLength']
            self.resource['metadata']['last_modified'] = \
                response['LastModified'].strftime('%s')
        elif self.resource['operation'] == 'GetObject':
            self.resource['metadata']['etag'] = response['ETag'].strip('"')
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
        self.resource['name'] = request_data['StreamName']

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
        self.resource['name'] = request_data['TopicArn'].split(':')[-1]

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
        # TODO: move everything from __init__ to a dedicated "run" function,
        # TODO: and then move these lines after the 'super' call.
        self.RESPONSE_TO_FUNC.update(
            {'Scan': self.process_scan_response,
             'GetItem': self.process_get_item_response,
             'ListTables': self.process_list_tables_response}
        )

        self.OPERATION_TO_FUNC.update(
            {'PutItem': self.process_put_item_op,
             'UpdateItem': self.process_update_item_op,
             'GetItem': self.process_get_item_op,
             'DeleteItem': self.process_delete_item_op,
             }
        )

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
        self.request_data = request_data
        self.resource['name'] = request_data.get('TableName', 'DynamoDBEngine')
        self.OPERATION_TO_FUNC.get(self.resource['operation'], empty_func)()

    def update_response(self, response):
        """
        Adds response data to event.
        :param response: Response from botocore
        :return: None
        """
        super(BotocoreDynamoDBEvent, self).update_response(response)
        self.RESPONSE_TO_FUNC.get(self.resource['operation'], empty_func)()

    def process_get_item_op(self):
        self.resource['metadata']['Key'] = self.request_data['Key']

    def process_put_item_op(self):
        self.resource['metadata']['Item'] = self.request_data['Item']
        self.store_item_hash()

    def process_delete_item_op(self):
        self.resource['metadata']['Key'] = self.request_data['Key']
        self.store_item_hash()

    def process_update_item_op(self):
        self.resource['metadata']['Update Parameters'] = {
            'Key': self.request_data['Key'],
            'Expression Attribute Values': self.request_data.get(
                'ExpressionAttributeValues', None),
            'Update Expression': self.request_data.get(
                'UpdateExpression',
                None
            ),
        }

    def process_scan_response(self, response):
        self.resource['metadata']['Items Count'] = response['Count']
        self.resource['metadata']['Items'] = response['Items']
        self.resource['metadata']['Scanned Items Count'] = \
            response['ScannedCount']

    def process_get_item_response(self, response):
        self.resource['metadata']['Item'] = response['Item']

    def process_list_tables_response(self, response):
        self.resource['metadata']['Table Names'] = \
            ', '.join(response['TableNames'])

    def store_item_hash(self):
        deser = TypeDeserializer()
        item = self.resource['metadata']['Item']

        # Try to deserialize the data in order to remove dynamoDB data types.
        for key in item:
            try:
                item[key] = deser.deserialize(item[key])
            except (TypeError, AttributeError):
                break
        self.resource['metadata']['item_hash'] = hashlib.md5(
            json.dumps(item, sort_keys=True).encode('utf-8')).hexdigest()


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

        self.resource['name'] = request_data['FunctionName']
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
