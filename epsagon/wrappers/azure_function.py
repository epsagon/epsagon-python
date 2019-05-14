"""
Wrapper for Azure Function.
"""

from __future__ import absolute_import
import time
import traceback
import functools
from ..trace import trace_factory
from ..runners.azure_function import AzureFunctionRunner


def azure_wrapper(func):
    """Epsagon's Azure Function wrapper."""

    @functools.wraps(func)
    def _azure_wrapper(*args, **kwargs):
        """
        general Azure function wrapper
        """
        trace = trace_factory.get_or_create_trace()
        trace.prepare()

        # Trigger event is not supported yet.

        runner = AzureFunctionRunner(time.time())
        trace.add_event(runner)

        try:
            result = func(*args, **kwargs)
            return result
        except Exception as exception:
            runner.set_exception(exception, traceback.format_exc())
            raise
        finally:
            runner.terminate()
            trace.send_traces()

    return _azure_wrapper
