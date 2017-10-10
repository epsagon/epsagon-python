import uuid
import time
from patcher import patch_all
import events


def lambda_wrapper(func):
    def _lambda_wrapper(*args, **kwargs):
        event, context = args

        # Setting for later use
        events.transaction_id = str(uuid.uuid4())
        events.function_name = context.__dict__['function_name']

        event = events.Event(
            event_id=context.__dict__['aws_request_id'],
            event_type='lambda_init',
            service_type='lambda',
            service_name=events.function_name,
            duration=0,
            end_reason=events.Event.ER_OK,
            metadata={
                'event': event,
                'log_stream_name': context.__dict__['log_stream_name'],
                'function_name': context.__dict__['function_name'],
                'function_version': context.__dict__['function_version'],
            }
        )

        exception = None
        try:
            result = func(*args, **kwargs)
        except Exception, ex:
            import traceback
            event.end_reason = events.Event.ER_EXCEPTION
            event.metadata['exception'] = ex.message
            event.metadata['traceback'] = traceback.format_exc()
            exception = ex
        event.duration = time.time() - event.timestamp
        events.events.append(event)
        try:
            events.send_to_server()
        except:
            return 'error sending'

        if exception is None:
            return result
        else:
            raise exception
    return _lambda_wrapper

patch_all()

# import requests
# import boto3
# requests.get('https://getalent.io/')
# lambda_client = boto3.client('lambda',
#                              aws_access_key_id='AKIAIJ46YIHLRQAY725A',
#                              aws_secret_access_key='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',
#                              region_name='us-west-2')
# s3_client = boto3.client('s3',
#                              aws_access_key_id='AKIAIJ46YIHLRQAY725A',
#                              aws_secret_access_key='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',
#                              region_name='us-west-2')
# msg = {'a': 1}
# import simplejson
# msg = simplejson.dumps(msg)
# results = s3_client.list_objects(Bucket='ran-arch-logs')
# invoke_response = lambda_client.invoke(FunctionName="create-thumbnail",
#                                        InvocationType='Event',
#                                        Payload=msg)
#
# print simplejson.dumps([event.get_dict() for event in events.events])