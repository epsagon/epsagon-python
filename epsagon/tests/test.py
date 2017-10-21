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
