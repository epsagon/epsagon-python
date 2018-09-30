"""
Runner for a general python function
"""

from __future__ import absolute_import
import uuid
import json
from ..event import BaseEvent
from ..utils import add_data_if_needed


class PythonRunner(BaseEvent):
    """
    Represents general python event runner.
    """

    ORIGIN = 'runner'
    RESOURCE_TYPE = 'python_function'
    OPERATION = 'invoke'

    def __init__(
            self,
            start_time,
            wrapped_function,
            wrapped_args,
            wrapped_kwargs
    ):
        """
        Initialize.
        :param start_time: event's start time (epoch).
        :param wrapped_function: the function this runner is wrapping.
        :param wrapped_args: the arguments the function was called with.
        :param wrapped_kwargs: the keyword arguments the function was
               called with.
        """

        super(PythonRunner, self).__init__(start_time)

        self.event_id = str(uuid.uuid4())
        self.resource['name'] = wrapped_function.__name__
        self.resource['operation'] = self.OPERATION
        self.resource['metadata'] = {
            'module': wrapped_function.__module__,
            'args_length': len(wrapped_args),
            'kwargs_length': len(wrapped_kwargs)
        }

        # Add arguments only if they are serializable.
        try:
            json.dumps(wrapped_args)
            add_data_if_needed(
                self.resource['metadata'],
                'Arguments',
                wrapped_args
            )
        except TypeError:
            pass
