"""
botocore events module.
"""

# pylint: disable=C0302
from __future__ import absolute_import

import hashlib
import traceback
import simplejson as json
from boto3.dynamodb.types import TypeDeserializer
from botocore.exceptions import ClientError
from ..trace import tracer
from ..event import BaseEvent
from ..utils import add_data_if_needed


# pylint: disable=W0613
def empty_func(*args):
    """
    A dummy function.
    :return: None
    """


class BotocoreEvent(BaseEvent):
    """
    Represents base botocore event.
    """

    ORIGIN = 'botocore'
    RESOURCE_TYPE = 'botocore'
    RESPONSE_TO_FUNC = {}
    OPERATION_TO_FUNC = {}

    # pylint: disable=W0613
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
        self.resource['metadata']['Retry Attempts'] = \
            response['ResponseMetadata']['RetryAttempts']
        self.resource['metadata']['Status Code'] = \
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
            files = [
                [str(x['Key']).strip('"'), x['Size'], x['ETag']]
                for x in response.get('Contents', [])
            ]
            add_data_if_needed(self.resource['metadata'], 'files', files)

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
        if 'Data' in request_data:
            add_data_if_needed(
                self.resource['metadata'],
                'data',
                request_data['Data']
            )
        if 'PartitionKey' in request_data:
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

        if self.resource['operation'] == 'CreateTopic':
            self.resource['name'] = request_data.get('Name', 'N/A')
        else:
            arn = request_data.get(
                'TopicArn',
                request_data.get('TargetArn', 'N/A')
            )
            self.resource['name'] = arn.split(':')[-1]

        if 'Message' in request_data:
            add_data_if_needed(
                self.resource['metadata'],
                'Notification Message',
                request_data['Message']
            )

    def update_response(self, response):
        """
        Adds response data to event.
        :param response: Response from botocore
        :return: None
        """

        super(BotocoreSNSEvent, self).update_response(response)

        if self.resource['operation'] == 'Publish':
            self.resource['metadata']['message_id'] = response['MessageId']


class BotocoreSQSEvent(BotocoreEvent):
    """
    Represents SQS botocore event.
    """
    RESOURCE_TYPE = 'sqs'

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
        self.RESPONSE_TO_FUNC.update(
            {'SendMessage': self.process_send_message_response,
             'ReceiveMessage': self.process_receive_message_response}
        )
        _, request_data = args
        self.request_data = request_data
        self.response = response

        super(BotocoreSQSEvent, self).__init__(
            wrapped,
            instance,
            args,
            kwargs,
            start_time,
            response,
            exception
        )

        if 'QueueUrl' in request_data:
            self.resource['name'] = request_data['QueueUrl'].split('/')[-1]
        elif 'QueueName' in request_data:
            self.resource['name'] = request_data['QueueName']

        # Currently tracing only first entry
        entry = request_data['Entries'][0] if (
                'Entries' in request_data) else request_data
        if 'MessageBody' in entry:
            add_data_if_needed(
                self.resource['metadata'],
                'Message Body',
                entry['MessageBody']
            )

    def update_response(self, response):
        """
        Adds response data to event.
        :param response: Response from botocore
        """
        super(BotocoreSQSEvent, self).update_response(response)
        self.RESPONSE_TO_FUNC.get(self.resource['operation'], empty_func)()

    def process_send_message_response(self):
        """
        Process the send message response
        """
        self.resource['metadata']['Message ID'] = self.response['MessageId']
        self.resource['metadata']['MD5 Of Message Body'] = (
            self.response['MD5OfMessageBody']
        )

    # pylint: disable=invalid-name
    def process_receive_message_response(self):
        """
        Process the receive message response -
            notice that only first message is traced
        """
        if 'Messages' in self.response:
            messages_number = len(self.response['Messages'])
            self.resource['metadata']['Message ID'] = (
                self.response['Messages'][0]['MessageId']
            )
            self.resource['metadata']['MD5 Of Message Body'] = (
                self.response['Messages'][0]['MD5OfBody']
            )
        else:
            messages_number = 0

        self.resource['metadata']['Number Of Messages'] = messages_number


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
        self.RESPONSE_TO_FUNC.update({
            'Scan': self.process_query_and_scan_response,
            'Query': self.process_query_and_scan_response,
            'GetItem': self.process_get_item_response,
            'BatchGetItem': self.process_batch_get_response,
            'ListTables': self.process_list_tables_response
        })

        self.OPERATION_TO_FUNC.update({
            'PutItem': self.process_put_item_op,
            'UpdateItem': self.process_update_item_op,
            'GetItem': self.process_get_item_op,
            'DescribeTable': self.process_describe_table_op,
            'DeleteItem': self.process_delete_item_op,
            'BatchWriteItem': self.process_batch_write_op,
            'BatchGetItem': self.process_batch_get_op,
            'Scan': self.process_scan_op,
            'Query': self.process_query_op
        })

        _, request_data = args
        self.request_data = request_data
        self.response = response
        self.deserializer = TypeDeserializer()

        super(BotocoreDynamoDBEvent, self).__init__(
            wrapped,
            instance,
            args,
            kwargs,
            start_time,
            response,
            exception
        )
        self.OPERATION_TO_FUNC.get(self.resource['operation'], empty_func)()

    def update_response(self, response):
        """
        Adds response data to event.
        :param response: Response from botocore
        """
        super(BotocoreDynamoDBEvent, self).update_response(response)
        self.RESPONSE_TO_FUNC.get(self.resource['operation'], empty_func)()

    def process_get_item_op(self):
        """
        Process the get item operation.
        """
        self.resource['name'] = self.request_data['TableName']
        self.resource['metadata']['Key'] = self.request_data['Key']

    def process_put_item_op(self):
        """
        Process the put item operation.
        """
        self.resource['name'] = self.request_data['TableName']
        if 'Item' in self.request_data:
            item = self.request_data['Item']
            add_data_if_needed(self.resource['metadata'], 'Item', item)
            self.store_item_hash(item)

    def process_delete_item_op(self):
        """
        Process the delete item operation.
        """
        self.resource['name'] = self.request_data['TableName']
        deserialized_key = self._deserialize_item(self.request_data['Key'])
        self.resource['metadata']['item_hash'] = hashlib.md5(
            json.dumps(deserialized_key).encode('utf-8')
        ).hexdigest()
        add_data_if_needed(
            self.resource['metadata'],
            'Key',
            self.request_data['Key']
        )

    def process_describe_table_op(self):
        """
        Process the describe tables operation.
        """
        self.resource['name'] = self.request_data['TableName']

    def process_update_item_op(self):
        """
        Process the update item operation.
        """
        self.resource['name'] = self.request_data['TableName']
        deserialized_key = self._deserialize_item(self.request_data['Key'])
        self.resource['metadata']['item_hash'] = hashlib.md5(
            json.dumps(deserialized_key).encode('utf-8')
        ).hexdigest()

        self.resource['metadata']['Update Parameters'] = {
            'Key': self.request_data['Key'],
            'Expression Attribute Values': self.request_data.get(
                'ExpressionAttributeValues', None),
            'Update Expression': self.request_data.get(
                'UpdateExpression',
                None
            ),
        }

    def process_batch_write_op(self):
        """
        Process the batch write operation.
        """
        table_name = list(self.request_data['RequestItems'].keys())[0]
        self.resource['name'] = table_name
        added_items = []
        deleted_keys = []
        for item in self.request_data['RequestItems'][table_name]:
            if 'PutRequest' in item:
                added_items.append(item['PutRequest']['Item'])
            if 'DeleteRequest' in item:
                deleted_keys.append(item['DeleteRequest']['Key'])

        if deleted_keys:
            add_data_if_needed(
                self.resource['metadata'],
                'Deleted Keys',
                deleted_keys
            )
        if added_items:
            add_data_if_needed(
                self.resource['metadata'],
                'Added Items',
                added_items
            )

    def process_batch_get_op(self):
        """
        Process the batch get item operation.
        """
        table_name = list(self.request_data['RequestItems'].keys())[0]
        self.resource['name'] = table_name
        keys = [
            key for key in
            self.request_data['RequestItems'][table_name]['Keys']
        ]

        self.resource['metadata']['Keys'] = keys

    def process_query_op(self):
        """
        Process the query operation.
        """
        self.resource['name'] = self.request_data['TableName']
        request_data = self.request_data.copy()
        if tracer.metadata_only:
            # Remove parameters containing non-metadata
            data_parameters = [
                'KeyConditions',
                'QueryFilter',
                'ExclusiveStartKey',
                'ProjectionExpression',
                'FilterExpression',
                'KeyConditionExpression',
                'ExpressionAttributeValues'
            ]
            for parameter in data_parameters:
                request_data.pop(parameter, None)
        self.resource['metadata']['Parameters'] = request_data

    def process_scan_op(self):
        """
        Process the scan operation.
        """
        self.resource['name'] = self.request_data['TableName']
        request_data = self.request_data.copy()
        if tracer.metadata_only:
            # Remove parameters containing non-metadata
            data_parameters = [
                'ScanFilter'
                'ExclusiveStartKey',
                'ProjectionExpression',
                'FilterExpression',
                'ExpressionAttributeValues'
            ]
            for parameter in data_parameters:
                request_data.pop(parameter, None)
        self.resource['metadata']['Parameters'] = request_data

    def process_get_item_response(self):
        """
        Process the get item response.
        """
        self.resource['name'] = self.request_data['TableName']
        if 'Item' in self.response:
            add_data_if_needed(
                self.resource['metadata'],
                'Item',
                self.response['Item']
            )

    def process_batch_get_response(self):
        """
        Process the batch get item response.
        """
        table_name = list(self.request_data['RequestItems'].keys())[0]
        self.resource['name'] = table_name
        add_data_if_needed(
            self.resource['metadata'],
            'Items',
            self.response['Responses'][table_name]
        )

    def process_list_tables_response(self):
        """
        Process the list tables response.
        """
        self.resource['name'] = 'DynamoDBEngine'
        self.resource['metadata']['Table Names'] = \
            ', '.join(self.response['TableNames'])

    def process_query_and_scan_response(self):
        """
        Process the query/scan response
        """
        response_data = self.response.copy()
        if tracer.metadata_only:
            # Remove parameters containing non-metadata
            response_data.pop('Items', None)
            response_data.pop('LastEvaluatedKey', None)
        self.resource['metadata']['Response'] = response_data

    def store_item_hash(self, item):
        """
        Store the item hash in the metadata.
        :param item: The item to store the hash for.
        """
        deserializer = TypeDeserializer()

        # Try to deserialize the data in order to remove dynamoDB data types.
        for key in item:
            try:
                item[key] = deserializer.deserialize(item[key])
            except (TypeError, AttributeError):
                break
        self.resource['metadata']['item_hash'] = hashlib.md5(
            json.dumps(item, sort_keys=True).encode('utf-8')).hexdigest()

    def _deserialize_item(self, item):
        """
        Deserialize DynamoDB Item in order to remove types definitions.
        :param item: The item to deserialize.
        :return: Deserialized item.
        """
        deserialized_item = item.copy()
        for key in item:
            try:
                deserialized_item[key] = self.deserializer.deserialize(
                    item[key]
                )
            except (TypeError, AttributeError):
                break
        return deserialized_item


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
            self.resource['metadata']['destination'] = \
                request_data['Destination']
            self.resource['metadata']['subject'] = \
                request_data['Message']['Subject']

            add_data_if_needed(
                self.resource['metadata'],
                'body',
                request_data['Message']['Body']
            )

    def update_response(self, response):
        """
        Adds response data to event.
        :param response: Response from botocore
        :return: None
        """

        super(BotocoreSESEvent, self).update_response(response)

        if self.resource['operation'] == 'SendEmail':
            self.resource['metadata']['message_id'] = response['MessageId']


class BotocoreAthenaEvent(BotocoreEvent):
    """
    Represents Athena botocore event
    """
    RESOURCE_TYPE = 'athena'

    def __init__(self, wrapped, instance, args, kwargs, start_time, response,
                 exception):
        self.RESPONSE_TO_FUNC.update(
            {'GetQueryExecution': self.process_get_query_response,
             'GetQueryResults': self.process_query_results_response,
             'StartQueryExecution': self.process_start_query_response,
             }
        )

        self.OPERATION_TO_FUNC.update(
            {'StartQueryExecution': self.process_start_query_operation,
             'GetQueryExecution': self.process_general_query_operation,
             'GetQueryResults': self.process_general_query_operation,
             'StopQueryExecution': self.process_general_query_operation,
             }
        )

        super(BotocoreAthenaEvent, self).__init__(
            wrapped,
            instance,
            args,
            kwargs,
            start_time,
            response,
            exception
        )

        self.OPERATION_TO_FUNC.get(
            self.resource['operation'], empty_func)(args, kwargs)

    def update_response(self, response):
        """
        Adds response data to event.
        :param response: Response from botocore's Athena Client
        """
        super(BotocoreAthenaEvent, self).update_response(response)

        self.RESPONSE_TO_FUNC.get(
            self.resource['operation'], empty_func)(response)

    def process_start_query_operation(self, args, _):
        """
        Process StartQueryExecution operation
        :param args: command arguments
        :param _: unused, kwargs
        :return: None
        """
        _, request_args = args

        self.resource['metadata']['Database'] = \
            request_args.get('QueryExecutionContext', {}).get('Database', None)

        add_data_if_needed(self.resource['metadata'], 'Query',
                           request_args['QueryString'])

    def process_get_query_response(self, response):
        """
        Process GetQueryExecution response
        :param response: response from Athena Client
        :return: None
        """
        metadata = self.resource['metadata']

        response_details = response['QueryExecution']

        metadata['Query Status'] = \
            response_details.get('Status', {}).get('State', None)

        metadata['Result Location'] = \
            response_details.get('ResultConfiguration', {}). \
                get('OutputLocation', None)

        metadata['Query ID'] = response_details['QueryExecutionId']
        add_data_if_needed(metadata, 'Query', response_details['Query'])

    def process_general_query_operation(self, args, _):
        """
        Process generic Athena Query operations
        :param args: command arguments
        :param _: unused, kwargs
        :return: None
        """
        _, request_args = args
        self.resource['metadata']['Query ID'] = request_args['QueryExecutionId']

    def process_query_results_response(self, response):
        """
        Process GetQueryResults response
        :param response: response from Athena Client
        :return: None
        """
        self.resource['metadata']['Query Rows Count'] = \
            len(response.get('ResultSet', {}).get('Rows', []))

    def process_start_query_response(self, response):
        """
        Process StartQueryExecution response
        :param response: response from Athena Client
        :return: None
        """
        self.resource['metadata']['Query ID'] = response['QueryExecutionId']


class BotocoreFirehoseEvent(BotocoreEvent):
    """
    Represents Firehose botocore event
    """
    RESOURCE_TYPE = 'firehose'

    def __init__(self, wrapped, instance, args, kwargs, start_time, response,
                 exception):
        self.RESPONSE_TO_FUNC.update({
            'PutRecord': self.put_record_response,
            'PutRecordBatch': self.put_record_batch_response,
        })

        self.OPERATION_TO_FUNC.update({
            'PutRecord': self.put_record_operation,
            'PutRecordBatch': self.put_record_batch_operation,
        })

        super(BotocoreFirehoseEvent, self).__init__(
            wrapped,
            instance,
            args,
            kwargs,
            start_time,
            response,
            exception
        )

        self.OPERATION_TO_FUNC.get(self.resource['operation'], empty_func)(
            args,
            kwargs
        )

    def update_response(self, response):
        """
        Adds response data to event.
        :param response: Response from botocore's Firehose Client
        """
        super(BotocoreFirehoseEvent, self).update_response(response)

        self.RESPONSE_TO_FUNC.get(self.resource['operation'], empty_func)(
            response
        )

    def put_record_operation(self, args, _):
        """
        Process PutRecord operation
        :param args: command arguments
        :param _: unused, kwargs
        :return: None
        """
        _, request_args = args
        self.resource['name'] = request_args['DeliveryStreamName']

    def put_record_response(self, response):
        """
        Process PutRecord response
        :param response: response from Firehose Client
        :return: None
        """
        self.resource['metadata']['record_id'] = response['RecordId']

    def put_record_batch_operation(self, args, _):
        """
        Process PutRecordBatch operation
        :param args: command arguments
        :param _: unused, kwargs
        :return: None
        """
        _, request_args = args
        self.resource['name'] = request_args['DeliveryStreamName']
        self.resource['metadata']['records_count'] = len(
            request_args['Records']
        )

    def put_record_batch_response(self, response):
        """
        Process PutRecordBatch response
        :param response: response from Firehose Client
        :return: None
        """
        metadata = self.resource['metadata']
        metadata['Failed Put Count'] = response['FailedPutCount']
        if response['RequestResponses']:
            metadata['record_id'] = response['RequestResponses'][0]['RecordId']


class BotocoreKMSEvent(BotocoreEvent):
    """
    Represents KMS botocore event
    """
    RESOURCE_TYPE = 'kms'

    def __init__(self, wrapped, instance, args, kwargs, start_time, response,
                 exception):
        self.RESPONSE_TO_FUNC.update({
            'Decrypt': self.decrypt_response,
            'Encrypt': self.encrypt_response,
        })

        self.OPERATION_TO_FUNC.update({
            'Decrypt': self.decrypt_operation,
            'Encrypt': self.encrypt_operation,
        })

        super(BotocoreKMSEvent, self).__init__(
            wrapped,
            instance,
            args,
            kwargs,
            start_time,
            response,
            exception
        )

        self.resource['name'] = 'KMS'
        self.OPERATION_TO_FUNC.get(self.resource['operation'], empty_func)(
            args,
            kwargs
        )

    def update_response(self, response):
        """
        Adds response data to event.
        :param response: Response from botocore's KMS Client
        """
        super(BotocoreKMSEvent, self).update_response(response)

        self.RESPONSE_TO_FUNC.get(self.resource['operation'], empty_func)(
            response
        )

    def decrypt_operation(self, args, _):
        """
        Process Decrypt operation
        :param args: command arguments
        :param _: unused, kwargs
        :return: None
        """
        _, request_args = args
        self.resource['metadata']['cipher_blob_size'] = len(
            request_args['CiphertextBlob']
        )

    def decrypt_response(self, response):
        """
        Process Decrypt response
        :param response: response from KMS Client
        :return: None
        """
        self.resource['metadata']['key_id'] = response['KeyId']
        self.resource['metadata']['plaintext_size'] = len(response['Plaintext'])

    def encrypt_operation(self, args, _):
        """
        Process Encrypt operation
        :param args: command arguments
        :param _: unused, kwargs
        :return: None
        """
        _, request_args = args
        self.resource['metadata']['key_id'] = request_args['KeyId']
        self.resource['metadata']['plaintext_size'] = len(
            request_args['Plaintext']
        )

    def encrypt_response(self, response):
        """
        Process Encrypt response
        :param response: response from KMS Client
        :return: None
        """
        self.resource['metadata']['cipher_blob_size'] = len(
            response['CiphertextBlob']
        )


class BotocoreSSMEvent(BotocoreEvent):
    """
    Represents SSM botocore event
    """
    RESOURCE_TYPE = 'ssm'

    def __init__(self, wrapped, instance, args, kwargs, start_time, response,
                 exception):
        self.RESPONSE_TO_FUNC.update({
            'GetParameters': self.get_params_response,
        })

        self.OPERATION_TO_FUNC.update({
            'GetParameters': self.get_params_operation,
        })

        super(BotocoreSSMEvent, self).__init__(
            wrapped,
            instance,
            args,
            kwargs,
            start_time,
            response,
            exception
        )

        self.resource['name'] = 'SSM'
        self.OPERATION_TO_FUNC.get(self.resource['operation'], empty_func)(
            args,
            kwargs
        )

    def update_response(self, response):
        """
        Adds response data to event.
        :param response: Response from botocore's SSM Client
        """
        super(BotocoreSSMEvent, self).update_response(response)

        self.RESPONSE_TO_FUNC.get(self.resource['operation'], empty_func)(
            response
        )

    def get_params_operation(self, args, _):
        """
        Process GetParameters operation
        :param args: command arguments
        :param _: unused, kwargs
        :return: None
        """
        _, request_args = args
        self.resource['metadata']['Names'] = str(request_args.get('Names', ''))
        self.resource['metadata']['With Decryption'] = (
            request_args.get('WithDecryption', True)
        )

    def get_params_response(self, response):
        """
        Process GetParameters response
        :param response: response from SSM Client
        :return: None
        """
        self.resource['metadata']['Parameters'] = response['Parameters']
        self.resource['metadata']['Invalid Parameters'] = str(
            response.get('InvalidParameters', '')
        )


class BotocoreStepFunctionEvent(BotocoreEvent):
    """
    Represents Step Function botocore event
    """
    RESOURCE_TYPE = 'sfn'
    REAL_RESOURCE_TYPE = 'stepfunctions'

    DEFAULT_EXECTUTION_NAME = 'Unnamed Execution'

    def __init__(self, wrapped, instance, args, kwargs, start_time, response,
                 exception):
        self.RESPONSE_TO_FUNC.update({
            'StartExecution': self.process_start_exec_response,
        })

        self.OPERATION_TO_FUNC.update({
            'StartExecution': self.process_start_exec_operation,
        })

        super(BotocoreStepFunctionEvent, self).__init__(
            wrapped,
            instance,
            args,
            kwargs,
            start_time,
            response,
            exception
        )

        # Fix resource type
        self.resource['type'] = self.REAL_RESOURCE_TYPE
        self.OPERATION_TO_FUNC.get(
            self.resource['operation'],
            empty_func
        )(args, kwargs)

    def update_response(self, response):
        """
        Adds response data to event.
        :param response: Response from botocore's Athena Client
        """
        super(BotocoreStepFunctionEvent, self).update_response(response)

        self.RESPONSE_TO_FUNC.get(
            self.resource['operation'],
            empty_func
        )(response)

    def process_start_exec_operation(self, args, _):
        """
        Process startExecution operation
        :param args: command arguments
        :param _: unused, kwargs
        :return: None
        """
        _, request_args = args

        self.resource['name'] = request_args['stateMachineArn'].split(':')[-1]
        self.resource['metadata']['State Machine ARN'] = (
            request_args['stateMachineArn']
        )
        self.resource['metadata']['Execution Name'] = (
            request_args.get('name', self.DEFAULT_EXECTUTION_NAME)
        )

        add_data_if_needed(
            self.resource['metadata'],
            'Input',
            request_args['input']
        )

    def process_start_exec_response(self, response):
        """
        Process startExecution response
        :param response: response from Step function Client
        :return: None
        """

        self.resource['metadata']['Execution Arn'] = response.get(
            'executionArn',
            ''
        )


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

        func_name = request_data.get('FunctionName', '')
        if ':' in func_name:
            func_name = func_name.split(':')[-1]

        self.resource['name'] = func_name
        if 'Payload' in request_data:
            add_data_if_needed(
                self.resource['metadata'],
                'payload',
                request_data['Payload']
            )
        if 'InvokeArgs' in request_data and \
                isinstance(request_data['InvokeArgs'], str):
            add_data_if_needed(
                self.resource['metadata'],
                'payload',
                request_data['InvokeArgs']
            )


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
        """
        Create an event according to the given instance_type.
        :param wrapped:
        :param instance:
        :param args:
        :param kwargs:
        :param start_time:
        :param response:
        :param exception:
        :return:
        """
        instance_type = instance.__class__.__name__.lower()
        event_class = BotocoreEventFactory.FACTORY.get(
            instance_type,
            None
        )

        if event_class is not None:
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
