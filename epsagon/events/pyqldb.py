"""
pyqldb events module.
"""

from __future__ import absolute_import
from uuid import uuid4
import traceback

from epsagon.utils import add_data_if_needed
from ..event import BaseEvent
from ..trace import trace_factory


class QldbEvent(BaseEvent):
    """
    Represents base pyqldb event.
    """

    ORIGIN = 'qldb'
    RESOURCE_TYPE = 'qldb'

    #pylint: disable=W0613
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
        super(QldbEvent, self).__init__(start_time)

        self.event_id = 'qldb-{}'.format(str(uuid4()))
        self.resource['name'] = \
            getattr(instance.__getattribute__('_transaction')._session,# pylint: disable=W0212
                                                '_ledger_name')
        self.resource['operation'] = wrapped.__func__.__name__

        self.resource['metadata']['query'] = args[0]
        add_data_if_needed(self.resource['metadata'], 'parameters',
                            [args[i] for i in range(1, len(args))])

        add_data_if_needed(self.resource['metadata'], 'transaction_id',
                            getattr(instance, 'transaction_id'))

        if response is not None:
            self.update_response(response)

        if exception is not None:
            self.set_exception(exception, traceback.format_exc())


    def update_response(self, response):
        """
        Adds response data to event.
        :param response: Response from botocore
        :return: None
        """

        self.resource['metadata']['Results'] = [str(x) for x in response]
        self.resource['metadata']['response.consumed_information'] = \
            response.get_consumed_ios()
        self.resource['metadata']['response.timing_information'] = \
            response.get_timing_information()



class QldbEventFactory(object):
    """
    Factory class, generates Qldb event.
    """

    @staticmethod
    def create_event(wrapped, instance, args, kwargs, start_time, response,
                     exception):
        """
        Create a Qldb event.
        :param wrapped:
        :param instance:
        :param args:
        :param kwargs:
        :param start_time:
        :param response:
        :param exception:
        :return:
        """
        event = QldbEvent(
            wrapped,
            instance,
            args,
            kwargs,
            start_time,
            response,
            exception
        )
        trace_factory.add_event(event)
