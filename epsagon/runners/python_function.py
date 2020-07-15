"""
Runner for a general python function
"""

from __future__ import absolute_import
import uuid
import json
import epsagon.trace
from ..event import BaseEvent
from ..trace_encoder import TraceEncoder


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
        wrapped_kwargs,
        name=None
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
        self.resource['name'] = name if name else wrapped_function.__name__
        self.resource['operation'] = self.OPERATION

        self.resource['metadata'].update({
            'python.module': wrapped_function.__module__,
            'python.function.name': wrapped_function.__name__,
        })

        if wrapped_args:
            self.add_json_field('python.function.args', wrapped_args)
            self.resource['metadata']['python.function.args_length'] = len(
                wrapped_args
            )

        if wrapped_kwargs:
            self.add_json_field('python.function.kwargs', wrapped_kwargs)
            self.resource['metadata']['python.function.kwargs_length'] = len(
                wrapped_kwargs
            )

    def add_json_field(self, name, data):
        """
        Add a field to metadata with value `data` and name `name`,
            only if it is JSON serializable
        """
        if epsagon.trace.trace_factory.get_trace().metadata_only:
            return

        try:
            json.dumps(data, cls=TraceEncoder, encoding='latin1')
            self.resource['metadata'][name] = data
        except TypeError:
            pass
