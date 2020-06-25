"""
Azure sdk events module.
"""

# pylint: disable=C0302
from __future__ import absolute_import

import traceback
from uuid import uuid4
from importlib import import_module
from ..trace import trace_factory
from ..event import BaseEvent
from ..utils import add_data_if_needed

# Conditionally importing Azure error class
AzureError = Exception  # pylint: disable=invalid-name
try:
    AzureError = (  # pylint: disable=invalid-name
        import_module('azure.core.exceptions').AzureError
    )
except ImportError:
    pass


# pylint: disable=W0613
def empty_func(*args):
    """
    A dummy function.
    :return: None
    """


class AzureEvent(BaseEvent):
    """
    Represents base Azure SDK event.
    """

    ORIGIN = 'azure-sdk'
    RESOURCE_TYPE = 'azure-sdk'
    RESPONSE_TO_FUNC = {}
    OPERATION_TO_FUNC = {}

    # pylint: disable=W0613
    def __init__(
            self,
            wrapped,
            instance,
            args,
            kwargs,
            start_time,
            response,
            exception
    ):
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
        super(AzureEvent, self).__init__(start_time)
        self.event_id = 'azure-{}'.format(str(uuid4()))
        self.resource['operation'] = wrapped.__name__
        self.resource['metadata'] = {}

        if response is not None:
            self.update_response(response)

        if exception is not None:
            self.set_exception(exception, traceback.format_exc())

    def update_response(self, _response):
        """
        Adds response data to event.
        :param _response: Response from azure
        :return: None
        """
        self.RESPONSE_TO_FUNC.get(self.resource['operation'], empty_func)()

    def set_exception(self, exception, traceback_data, handled=True):
        """
        see {Event.set_exception}
        """
        super(AzureEvent, self).set_exception(
            exception,
            traceback_data,
            handled=handled
        )

        # Specific handling for azure errors
        if isinstance(exception, AzureError):
            self.event_id = exception.headers.get('x-ms-activity-id')
            self.resource['metadata']['azure_error'] = True
            self.resource['metadata']['status_code'] = exception.status_code
            self.resource['metadata']['error_message'] = exception.message
            self.resource['metadata']['reason'] = exception.reason


class AzureCosmosContainerEvent(AzureEvent):
    """
    Represents CosmosDB Container Azure event.
    """

    RESOURCE_TYPE = 'cosmos_db'

    def __init__(
            self,
            wrapped,
            instance,
            args,
            kwargs,
            start_time,
            response,
            exception
    ):
        """
        Initialize.
        """
        super(AzureCosmosContainerEvent, self).__init__(
            wrapped,
            instance,
            args,
            kwargs,
            start_time,
            response,
            exception
        )
        self.RESPONSE_TO_FUNC.update({
            'upsert_item': self.upsert_item_response,
        })

        self.OPERATION_TO_FUNC.update({
            'upsert_item': self.upsert_item_request,
            'delete_item': self.delete_item_request,
            'query_items': self.query_items_request,
        })
        self.kwargs = kwargs
        self.args = args
        self.response = response

        self.resource['metadata']['azure.location'] = (
            instance.client_connection.ReadEndpoint.split(
                '-'
            )[1].split('.')[0]
        )
        self.resource['metadata']['azure.cosmos.endpoint'] = (
            instance.client_connection.url_connection
        )
        _, database, _, container = instance.container_link.split('/')
        self.resource['name'] = container
        self.resource['metadata']['azure.cosmos.database_id'] = database
        self.resource['metadata']['azure.cosmos.container_id'] = container

        self.OPERATION_TO_FUNC.get(self.resource['operation'], empty_func)()

    def upsert_item_request(self):
        self.resource['metadata']['azure.cosmos.document_id'] = (
            self.args[0].get('id')
        )

    def query_items_request(self):
        self.resource['metadata']['azure.cosmos.query'] = (
            self.kwargs.get('query')
        )

    def delete_item_request(self):
        self.resource['metadata']['azure.cosmos.document_id'] = (
            self.args[0].get('id')
        )
        add_data_if_needed(
            self.resource['metadata'],
            'azure.cosmos.document',
            self.args[0]
        )

    def upsert_item_response(self):
        self.resource['metadata']['azure.cosmos.document.etag'] = (
            self.kwargs.get('_etag')
        )
        add_data_if_needed(
            self.resource['metadata'],
            'azure.cosmos.document',
            self.response
        )


class AzureEventFactory(object):
    """
    Factory class, generates azure sdk event.
    """

    CLASS_MAPPING = {
        'ContainerProxy': AzureCosmosContainerEvent,
    }

    @staticmethod
    def create_event(
        wrapped,
        instance,
        args,
        kwargs,
        start_time,
        response,
        exception
    ):
        """
        Create an event according to the given instance_type.
        """

        event_class = AzureEventFactory.CLASS_MAPPING.get(
            instance.__class__.__name__
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
