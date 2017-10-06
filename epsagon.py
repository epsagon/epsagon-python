import simplejson
import requests
import gzip
import uuid
from cStringIO import StringIO
from patcher import patch_all


messages_buffer = []
transaction_id = None
TRACES_URL = 'https://fib01keo54.execute-api.us-east-1.amazonaws.com/dev/'


def _send_to_server():
    global messages_buffer
    data = simplejson.dumps(messages_buffer)
    gzipped_data = StringIO()
    with gzip.GzipFile(fileobj=gzipped_data, mode='w') as gzipped_file:
        gzipped_file.write(data)
    requests.post(TRACES_URL, data=simplejson.dumps(messages_buffer))
    messages_buffer = []


def _lambda_wrapper(func):
    def lambda_wrapper(*args, **kwargs):
        global transaction_id
        transaction_id = str(uuid.uuid4())
        event, context = args
        messages_buffer.append({
            'endpoint': 'lambda',
            'type': 'lambda_init',
            'transaction_id': transaction_id,
            'aws_request_id': context.__dict__['aws_request_id'],
            'log_stream_name': context.__dict__['log_stream_name'],
            'function_name': context.__dict__['function_name'],
            'function_version': context.__dict__['function_version'],
            'event': event
        })
        result = func(*args, **kwargs)
        try:
            _send_to_server()
        except:
            return 'error sending'
        return result
    return lambda_wrapper

patch_all()

#import requests
#import boto3
#requests.get('https://getalent.io/')
#lambda_client = boto3.client('lambda',
#                             aws_access_key_id='AKIAIJ46YIHLRQAY725A',
#                             aws_secret_access_key='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',
#                             region_name='us-west-2')
#s3_client = boto3.client('s3',
#                             aws_access_key_id='AKIAIJ46YIHLRQAY725A',
#                             aws_secret_access_key='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',
#                             region_name='us-west-2')
#msg = {'a': 1}
#msg = simplejson.dumps(msg)
#results = s3_client.list_objects(Bucket='ran-arch-logs')
#invoke_response = lambda_client.invoke(FunctionName="create-thumbnail",
#                                       InvocationType='Event',
#                                       Payload=msg)
