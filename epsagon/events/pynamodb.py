"""
PynamoDB events module.
"""

from __future__ import absolute_import
import simplejson as json
from ..trace import tracer
from .botocore import BotocoreDynamoDBEvent


class NestedObject(object):
    """
    Creating a nested object based on a dict.
    """
    def __init__(self, **data):
        for k, v in data.items():
            if isinstance(v, dict):
                self.__dict__[k] = NestedObject(**v)
            else:
                self.__dict__[k] = v


class PynamoDBEventAdapter(object):
    """
    Factory class, generates PynamoDB event.
    """

    @staticmethod
    def create_event(wrapped, _instance, args, kwargs, start_time, response,
                     exception):
        """Creates DynamoDB event based on PynamoDB data"""
        new_args = (
            args[0].headers['X-Amz-Target'].decode('utf-8').split('.')[1],
            json.loads(args[0].body.decode('utf-8'))
        )

        new_instance = NestedObject(**{
            'meta': {
                'region_name': args[0].url.split('.')[1]
            }
        })

        new_response = {
            'ResponseMetadata': {
                'RequestId': response.headers['x-amzn-requestid'],
                'HTTPStatusCode': response.status_code,
                'RetryAttempts': None,
            },
        }
        new_response.update(response.json())
        event = BotocoreDynamoDBEvent(
            wrapped,
            new_instance,
            new_args,
            kwargs,
            start_time,
            new_response,
            exception
        )
        event.origin = 'pynamodb'
        event.resource['metadata'].pop('Retry Attempts')

        tracer.add_event(event)
