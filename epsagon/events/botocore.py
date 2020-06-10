"""
botocore events module.
"""

# pylint: disable=C0302
from __future__ import absolute_import

import hashlib
import traceback
from importlib import import_module
import simplejson as json
from epsagon.constants import STEP_DICT_NAME
from ..trace import trace_factory
from ..event import BaseEvent
from ..utils import add_data_if_needed, add_metadata_from_dict

# Conditionally importing boto3
ClientError = Exception  # pylint: disable=invalid-name
TypeDeserializer = None  # pylint: disable=invalid-name
ConditionExpressionBuilder = None  # pylint: disable=invalid-name
try:
    ClientError = (  # pylint: disable=invalid-name
        import_module('botocore.exceptions').ClientError
    )
    TypeDeserializer = (  # pylint: disable=invalid-name
        import_module('boto3.dynamodb.types').TypeDeserializer
    )
    ConditionExpressionBuilder = (  # pylint: disable=invalid-name
        import_module('boto3.dynamodb.conditions').ConditionExpressionBuilder
    )
except ImportError:
    pass


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

    def set_exception(self, exception, traceback_data, handled=True):
        """
        see {Event.set_exception}
        """
        super(BotocoreEvent, self).set_exception(
            exception,
            traceback_data,
            handled=handled
        )

        # Specific handling for botocore errors
        if (
            isinstance(exception, ClientError) and
            'ResponseMetadata' in exception.response
        ):
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
        elif self.resource['operation'] == 'CopyObject':
            self.resource['metadata']['source'] = request_data['CopySource']
            self.resource['metadata']['destination'] = request_data['Key']

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
        if self.resource['operation'] == 'PutRecords':
            self.resource['metadata']['failed_record_count'] = \
                response['FailedRecordCount']
            self.resource['metadata']['shard_id'] = \
                response['Records'][0]['ShardId']
            self.resource['metadata']['sequence_number'] = \
                response['Records'][0]['SequenceNumber']
            self.resource['metadata']['record_count'] = \
                len(response['Records'])


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

        self._process_request_data(request_data)

    def _process_request_data(self, request_data):
        """
        Process the SNS message request data - adding relevant message data
        :param request_data: the request_data to process
        """
        message_fields_description = {
            'Message': 'Notification Message',
            'MessageAttributes': 'Notification Message Attributes',
        }
        for field, description in message_fields_description.items():
            if field in request_data:
                add_data_if_needed(
                    self.resource['metadata'],
                    description,
                    request_data[field]
                )

        header_data = {
            key: value for key, value in request_data.items()
            if key not in message_fields_description
        }
        add_data_if_needed(
            self.resource['metadata'],
            'Notification Message Headers',
            header_data
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
        self.RESPONSE_TO_FUNC.update({
            'SendMessage': self.process_send_message_response,
            'SendMessageBatch': self.process_send_message_batch_response,
            'ReceiveMessage': self.process_receive_message_response
        })
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

    def process_send_message_batch_response(self):
        """
        Process the send message batch response
        """
        # Check for at least one message sent successfully
        if not self.response.get('Successful'):
            return
        message = self.response['Successful'][0]
        self.resource['metadata']['Message ID'] = message['MessageId']
        self.resource['metadata']['MD5 Of Message Body'] = (
            message['MD5OfMessageBody']
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
    CONDITION_FIELDS = ['FilterExpression', 'KeyConditionExpression']

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
        self.deserializer = TypeDeserializer() if TypeDeserializer else None

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
        if deserialized_key is not None:
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
        if deserialized_key is not None:
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
        keys = list(self.request_data['RequestItems'][table_name]['Keys'])

        self.resource['metadata']['Keys'] = keys

    def process_query_op(self):
        """
        Process the query operation.
        """
        self.resource['name'] = self.request_data['TableName']
        if ConditionExpressionBuilder is None:
            return

        request_data = self._stringify_conditions(self.request_data.copy())
        if trace_factory.metadata_only:
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
        if ConditionExpressionBuilder is None:
            return

        request_data = self._stringify_conditions(self.request_data.copy())
        if trace_factory.metadata_only:
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
        if self.response.get('Item'):
            add_data_if_needed(
                self.resource['metadata'],
                'Item',
                self.response['Item']
            )
        else:
            self.resource['metadata']['Item'] = 'null'

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
        if trace_factory.metadata_only:
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

    def _stringify_conditions(self, request_data):
        """
        convert Key and Attr object of DynamoDB to strings.
        :param request_data: DynamoDB request data
        :return: updated request data
        """
        for field in self.CONDITION_FIELDS:
            if field in request_data:
                try:
                    request_data[field] = str(
                        ConditionExpressionBuilder().build_expression(
                            request_data[field],
                            field == 'KeyConditionExpression'
                        )
                    )
                except Exception:  # pylint: disable=W0703
                    pass
        return request_data


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


class BotocoreCognitoEvent(BotocoreEvent):
    """
    Represents Cognito botocore event
    """
    RESOURCE_TYPE = 'cognitoidentityprovider'
    RESOURCE_TYPE_UPDATE = 'cognito-idp'

    def __init__(self, wrapped, instance, args, kwargs, start_time, response,
                 exception):
        self.RESPONSE_TO_FUNC.update({
            'AdminCreateUser': self.admin_create_user_res,
            'AdminListGroupsForUser': self.admin_list_user_group_res,
        })

        self.OPERATION_TO_FUNC.update({
            'AdminCreateUser': self.admin_create_user_op,
            'AdminListGroupsForUser': self.admin_list_user_group_op,
            'AdminSetUserPassword': self.admin_set_pass_op,
            'DescribeUserPool': self.describe_user_pool_op,
            'ListUsers': self.list_users_op,
            'UpdateUserPool': self.update_pool_op,
        })

        super(BotocoreCognitoEvent, self).__init__(
            wrapped,
            instance,
            args,
            kwargs,
            start_time,
            response,
            exception
        )
        self.resource['type'] = self.RESOURCE_TYPE_UPDATE

        self.OPERATION_TO_FUNC.get(self.resource['operation'], empty_func)(
            args,
            kwargs
        )

    def update_response(self, response):
        """
        Adds response data to event.
        :param response: Response from botocore's Cognito Client
        """
        super(BotocoreCognitoEvent, self).update_response(response)

        self.RESPONSE_TO_FUNC.get(self.resource['operation'], empty_func)(
            response
        )

    def admin_create_user_op(self, args, _):
        """
        Process AdminCreateUser operation
        :param args: command arguments
        :param _: unused, kwargs
        :return: None
        """
        _, request_args = args
        self.resource['name'] = request_args['UserPoolId']
        add_data_if_needed(
            self.resource['metadata'],
            'request',
            request_args
        )

    def admin_create_user_res(self, response):
        """
        Process AdminCreateUser response
        :param response: response from Client
        :return: None
        """
        self.resource['metadata']['user'] = response['User']

    def admin_list_user_group_op(self, args, _):
        """
        Process AdminListGroupsForUser operation
        :param args: command arguments
        :param _: unused, kwargs
        :return: None
        """
        _, request_args = args
        self.resource['name'] = request_args['UserPoolId']
        self.resource['metadata']['username'] = request_args['Username']

    def admin_list_user_group_res(self, response):
        """
        Process AdminListGroupsForUser response
        :param response: response from Client
        :return: None
        """
        add_data_if_needed(
            self.resource['metadata'],
            'groups',
            response['Groups']
        )

    def admin_set_pass_op(self, args, _):
        """
        Process AdminSetUserPassword operation
        :param args: command arguments
        :param _: unused, kwargs
        :return: None
        """
        _, request_args = args
        self.resource['name'] = request_args['UserPoolId']
        self.resource['metadata']['username'] = request_args['Username']
        self.resource['metadata']['permanent'] = request_args.get(
            'Permanent',
            False
        )

    def describe_user_pool_op(self, args, _):
        """
        Process DescribeUserPool operation
        :param args: command arguments
        :param _: unused, kwargs
        :return: None
        """
        _, request_args = args
        self.resource['name'] = request_args['UserPoolId']

    def list_users_op(self, args, _):
        """
        Process ListUsers operation
        :param args: command arguments
        :param _: unused, kwargs
        :return: None
        """
        _, request_args = args
        self.resource['name'] = request_args['UserPoolId']
        add_data_if_needed(
            self.resource['metadata'],
            'request',
            request_args
        )

    def update_pool_op(self, args, _):
        """
        Process UpdateUserPool operation
        :param args: command arguments
        :param _: unused, kwargs
        :return: None
        """
        _, request_args = args
        self.resource['name'] = request_args['UserPoolId']
        self.resource['metadata'].update(request_args)


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
        add_data_if_needed(
            self.resource['metadata'],
            'Names',
            str(request_args.get('Names', '')),
        )
        self.resource['metadata']['With Decryption'] = (
            request_args.get('WithDecryption', True)
        )

    def get_params_response(self, response):
        """
        Process GetParameters response
        :param response: response from SSM Client
        :return: None
        """
        add_data_if_needed(
            self.resource['metadata'],
            'Parameters',
            response['Parameters']
        )
        add_data_if_needed(
            self.resource['metadata'],
            'Invalid Parameters',
            str(response.get('InvalidParameters', ''))
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
            'SendTaskHeartbeat': self.process_send_task_heartbeat_response,
            'DescribeExecution': self.process_describe_execution_response,
        })

        self.OPERATION_TO_FUNC.update({
            'StartExecution': self.process_start_exec_operation,
            'SendTaskSuccess': self.process_send_task_success_exec_operation,
            'SendTaskHeartbeat': self.process_send_task_heartbeat_operation,
            'DescribeExecution': self.process_describe_execution_operation,
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

    def initialize_step_dict(self, request_args, params_property_name):
        try:
            machine_input = json.loads(request_args[params_property_name])
            self.resource['metadata']['steps_dict'] = (
                machine_input[STEP_DICT_NAME]
            )
        except Exception:  # pylint: disable=broad-except
            pass

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
        self.resource['name'] = self.REAL_RESOURCE_TYPE
        self.resource['metadata']['State Machine ARN'] = (
            request_args['stateMachineArn']
        )
        if 'name' in request_args:
            self.resource['metadata']['Execution Name'] = request_args['name']

        add_data_if_needed(
            self.resource['metadata'],
            'Input',
            request_args['input']
        )

        self.initialize_step_dict(request_args, 'input')

    def process_send_task_success_exec_operation(self, args, _):
        """
        Process sendTaskSuccess operation
        :param args: command arguments
        :param _: unused, kwargs
        :return: None
        """
        _, request_args = args

        self.initialize_step_dict(request_args, 'output')

    def process_send_task_heartbeat_operation(self, args, _):
        """
        Process sendTaskSuccess operation
        :param args: command arguments
        :param _: unused, kwargs
        :return: None
        """
        _, request_args = args
        add_metadata_from_dict(self.resource, request_args, 'taskToken')

    def process_describe_execution_operation(self, args, _):
        """
        Process sendTaskSuccess operation
        :param args: command arguments
        :param _: unused, kwargs
        :return: None
        """
        _, request_args = args
        add_metadata_from_dict(self.resource, request_args,
                                      'executionArn')

    def process_start_exec_response(self, response):
        """
        Process startExecution response
        :param response: response from Step function Client
        :return: None
        """
        add_metadata_from_dict(self.resource, response, 'executionArn')

    def process_send_task_heartbeat_response(self, response):
        """
        Process sendTaskHeartbeat response
        :param response: response from Step function Client
        :return: None
        """

        add_metadata_from_dict(self.resource, response,
                                      'ResponseMetadata')

    def process_describe_execution_response(self, response):
        """
        Process describeExecution response
        :param response: response from Step function Client
        :return: None
        """
        if isinstance(response, dict):
            for key in response:
                add_metadata_from_dict(self.resource, response, key)


class BotocoreLambdaEvent(BotocoreEvent):
    """
    Represents lambda botocore event.
    """

    RESOURCE_TYPE = 'lambda'
    AWS_ACCOUNT_IND = 4

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
            splitted_func_name = func_name.split(':')
            self.resource['metadata']['aws_account'] = splitted_func_name[
                self.AWS_ACCOUNT_IND
            ]
            func_name = splitted_func_name[-1]
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


class BotocoreEmr(BotocoreEvent):
    """
    Represents EMR botocore event.
    """

    RESOURCE_TYPE = 'emr'

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

        self.OPERATION_TO_FUNC.update({
            'AddJobFlowSteps': self.add_job_flow_steps_op,
            'TerminateJobFlows': self.terminate_job_flows_op,
            'ListClusters': self.list_clusters_op,
            'RunJobFlow': self.run_job_flow_op
        })

        self.RESPONSE_TO_FUNC.update({
            'DescribeCluster': self.describe_cluster_response,
            'DescribeStep': self.describe_step_response,
            'AddJobFlowSteps': self.add_job_flow_steps_response,
            'ListInstances': self.list_instances_response,
            'ListClusters': self.list_clusters_response,
            'RunJobFlow': self.run_job_flow_response
        })
        _, request_data = args
        self.request_data = request_data
        self.response = response

        super(BotocoreEmr, self).__init__(
            wrapped,
            instance,
            args,
            kwargs,
            start_time,
            response,
            exception
        )

        self.resource['name'] = request_data.get(
            'ClusterId',
            request_data.get('JobFlowId', 'EMR')
        )
        self.OPERATION_TO_FUNC.get(self.resource['operation'], empty_func)()

    def add_job_flow_steps_op(self):
        """
        Handle add job flow steps operation.
        """
        self.resource['metadata']['Steps'] = self.request_data['Steps']

    def terminate_job_flows_op(self):
        """
        Handle terminate job flows operation.
        """
        self.resource['metadata']['Job Flow IDs'] = self.request_data[
            'JobFlowIds']

    def list_clusters_op(self):
        """
        Handle list clusters operation.
        """
        self.resource['metadata']['Cluster States'] = self.request_data.get(
            'ClusterStates')

    def run_job_flow_op(self):
        """
        Handle run job flow operation.
        """
        self.resource['metadata']['Request'] = self.request_data

    def update_response(self, response):
        """
        Adds response data to event.
        :param response: Response from botocore
        """
        super(BotocoreEmr, self).update_response(response)
        self.RESPONSE_TO_FUNC.get(self.resource['operation'], empty_func)()

    def describe_cluster_response(self):
        """
        Handle describe cluster response.
        """
        cluster = self.response['Cluster']
        self.resource['metadata']['Status'] = cluster['Status']
        self.resource['metadata']['Cluster Name'] = cluster['Name']
        self.resource['metadata']['Cluster ID'] = cluster['Id']

    def describe_step_response(self):
        """
        Handle describe step response.
        """
        step = self.response['Step']
        self.resource['metadata']['Step Id'] = step['Id']
        self.resource['metadata']['Step Name'] = step['Name']
        self.resource['metadata']['Status'] = step['Status']
        self.resource['metadata']['Step Config'] = step['Config']

    def add_job_flow_steps_response(self):
        """
        Handle add job flow steps response.
        """
        self.resource['metadata']['Step Ids'] = self.response['StepIds']

    def list_instances_response(self):
        """
        Handle list instances response.
        """
        self.resource['metadata']['Instances'] = self.response['Instances']

    def list_clusters_response(self):
        """
        Handle list clusters response.
        """
        self.resource['metadata']['Clusters'] = self.response['Clusters']

    def run_job_flow_response(self):
        """
        Handle run job flow response.
        """
        self.resource['metadata']['Job Flow ID'] = self.response['JobFlowId']


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
            trace_factory.add_event(event)
