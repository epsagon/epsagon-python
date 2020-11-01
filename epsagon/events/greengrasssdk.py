"""
Greengrass events module.
"""

from __future__ import absolute_import
import traceback
from uuid import uuid4

from epsagon.utils import add_data_if_needed
from ..trace import trace_factory
from ..event import BaseEvent


class GreengrassPublishEvent(BaseEvent):
    """
    Represents Greengrass publish event.
    """

    ORIGIN = 'greengrasssdk'
    RESOURCE_TYPE = 'greengrass'

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
        super(GreengrassPublishEvent, self).__init__(start_time)

        self.event_id = 'greengrass-{}'.format(str(uuid4()))

        self.resource['name'] = kwargs.get('topic', 'N/A')
        self.resource['operation'] = 'publish'
        if kwargs.get('queueFullPolicy'):
            self.resource['metadata']['aws.greengrass.queueFullPolicy'] = (
                kwargs.get('queueFullPolicy')
            )

        add_data_if_needed(
            self.resource['metadata'],
            'aws.greengrass.payload',
            kwargs.get('payload')
        )

        if exception is not None:
            self.set_exception(exception, traceback.format_exc())


class GreengrassEventFactory(object):
    """
    Factory class, generates Greengrass event.
    """

    @staticmethod
    def create_event(wrapped, instance, args, kwargs, start_time, response,
                     exception):
        """
        Create an event according to the given api_name.
        """
        event = GreengrassPublishEvent(
            wrapped,
            instance,
            args,
            kwargs,
            start_time,
            response,
            exception
        )

        trace_factory.add_event(event)
