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
        # try:
        runner = AzureFunctionRunner(time.time(), context)
        trace.set_runner(runner)
        # except Exception as exception:  # pylint: disable=broad-except
        #     warnings.warn(
        #         'Could not create Azure Function runner',
        #         EpsagonWarning
        #     )
        #     return func(*args, **kwargs)

        # Create Trigger
        # try:
        runner = AzureFunctionRunner(time.time(), context)
        trace.set_runner(runner)
        # except Exception as exception:  # pylint: disable=broad-except
        #     warnings.warn(
        #         'Could not create Azure Function runner',
        #         EpsagonWarning
        #     )
        #     return func(*args, **kwargs)


        try:
            result = func(*args, **kwargs)
            return result
        except Exception as exception:
            runner.set_exception(exception, traceback.format_exc())
            raise
        finally:
            runner.terminate()
            trace_factory.send_traces()

    return _azure_wrapper
