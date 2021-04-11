"""
Cloud Object Storage events module.
"""

from __future__ import absolute_import
from uuid import uuid4
import traceback

from ..event import BaseEvent
from ..trace import trace_factory


class COSEvent(BaseEvent):
    """
    Represents base Cloud Object Storage event.
    """
    ORIGIN = 'tencent-cos'
    RESOURCE_TYPE = 'cos'

    # pylint: disable=W0613
    def __init__(self, wrapped, instance, args, kwargs, start_time, response,
                 exception):
        """
        Initialize the Cloud Object Storage event
        :param wrapped: wrapt's wrapped
        :param instance: wrapt's instance
        :param args: wrapt's args
        :param kwargs: wrapt's kwargs
        :param start_time: Start timestamp (epoch)
        :param response: response data
        :param exception: Exception (if happened)
        """

        super(COSEvent, self).__init__(start_time)
        self.event_id = 'cos-{}'.format(str(uuid4()))
        self.resource['name'] = kwargs['bucket']
        self.resource['operation'] = kwargs['method']
        self.resource['metadata'] = {
            # pylint: disable=protected-access
            'tencent.region': instance._conf._region,
            'tencent.cos.object_key': kwargs['url'].split('myqcloud.com/')[-1],
        }
        if response:
            self.resource['metadata'].update({
                'tencent.cos.request_id': response.headers['x-cos-request-id'],
                'tencent.status_code': response.status_code,
            })

        if exception is not None:
            self.resource['metadata'].update({
                'tencent.cos.request_id': exception.get_request_id(),
                'tencent.status_code': exception.get_status_code(),
            })
            self.set_exception(exception, traceback.format_exc())


class COSEventFactory(object):
    """
    Factory class, generates Cloud Object Storage event.
    """
    @staticmethod
    def create_event(wrapped, instance, args, kwargs, start_time, response,
                     exception):
        """
        Create a Cloud Object Storage event.
        """
        trace_factory.add_event(COSEvent(
            wrapped,
            instance,
            args,
            kwargs,
            start_time,
            response,
            exception
        ))
