"""
Wrapper for Azure Function.
"""

from __future__ import absolute_import
import time
import traceback
import warnings
import functools
from ..trace import trace_factory
from ..runners.azure_function import AzureFunctionRunner
from ..triggers.azure_function import AzureTriggerFactory
from ..common import EpsagonWarning


def azure_wrapper(func):
    """Epsagon's Azure Function wrapper."""

    @functools.wraps(func)
    def _azure_wrapper(*args, **kwargs):
        """
        general Azure function wrapper
        """
        trace = trace_factory.get_or_create_trace()
        trace.prepare()

        context = kwargs.get('context')
        if not context:
            return func(*args, **kwargs)

        # Create Runner
        try:
            runner = AzureFunctionRunner(time.time(), context)
            trace.set_runner(runner)
        except Exception as exception:  # pylint: disable=broad-except
            warnings.warn(
                'Could not create Azure Function runner: {}'.format(exception),
                EpsagonWarning
            )
            return func(*args, **kwargs)

        result = None
        try:
            result = func(*args, **kwargs)
        except Exception as exception:
            runner.set_exception(exception, traceback.format_exc())
            raise
        finally:
            runner.terminate()

        # Create Trigger
        try:
            azure_trigger = AzureTriggerFactory.factory(
                time.time(),
                kwargs,
                result
            )
            if azure_trigger:
                trace.add_event(azure_trigger)
        except Exception as exception:  # pylint: disable=broad-except
            warnings.warn(
                'Could not create Azure Function trigger: {}'.format(exception),
                EpsagonWarning
            )
            return func(*args, **kwargs)

        trace_factory.send_traces()
        return result

    return _azure_wrapper
