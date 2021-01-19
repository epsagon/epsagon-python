"""
kafka-python events.
"""

from __future__ import absolute_import
import traceback
from uuid import uuid4

from epsagon.utils import add_data_if_needed
from ..trace import trace_factory
from ..event import BaseEvent
from ..constants import EPSAGON_HEADER


class KafkaEvent(BaseEvent):
    """
    Represents base Kafka event.
    """

    ORIGIN = 'kafka'
    RESOURCE_TYPE = 'kafka'

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
        super(KafkaEvent, self).__init__(start_time)
        self.event_id = 'kafka-{}'.format(str(uuid4()))

        topic = args[0]
        headers = dict(kwargs['headers'])
        servers = instance.config['bootstrap_servers']
        if servers and isinstance(servers, list):
            # Take the first server if it is a list
            servers = servers[0]

        self.resource['name'] = topic
        self.resource['operation'] = 'send'
        self.resource['metadata'] = {
            'messaging.system': 'kafka',
            'messaging.destination': topic,
            'messaging.url': servers,
            'messaging.message_payload_size_bytes': (
                len(str(kwargs.get('value', '')))
            ),
        }
        if instance.config.get('client_id'):
            self.resource['metadata']['messaging.kafka.client_id'] = (
                instance.config['client_id']
            )
        if headers.get(EPSAGON_HEADER):
            self.resource['metadata'][EPSAGON_HEADER] = (
                headers[EPSAGON_HEADER]
            )
        if kwargs['key']:
            self.resource['metadata']['messaging.kafka.message_key'] = (
                kwargs['key']
            )

        add_data_if_needed(
            self.resource['metadata'],
            'messaging.headers',
            headers
        )

        add_data_if_needed(
            self.resource['metadata'],
            'messaging.message',
            kwargs['value']
        )

        if getattr(response, 'value', None) is not None:
            self.update_response(response.value)

        if exception is not None:
            self.set_exception(exception, traceback.format_exc())

    def update_response(self, response):
        """
        Adds response data to event.
        :param response: Response from botocore
        :return: None
        """
        self.resource['metadata']['messaging.kafka.partition'] = (
            response.partition
        )


class KafkaEventFactory(object):
    """
    Factory class, generates a kafka event.
    """

    @staticmethod
    def create_event(wrapped, instance, args, kwargs, start_time, response,
                     exception):
        """Create an event"""
        event = KafkaEvent(
            wrapped,
            instance,
            args,
            kwargs,
            start_time,
            response,
            exception
        )

        trace_factory.add_event(event)
