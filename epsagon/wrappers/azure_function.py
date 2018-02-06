"""
Wrapper for Azure Function.
"""

from __future__ import absolute_import
import time
import traceback
import functools
from ..trace import tracer
from ..runners.azure_function import AzureFunctionRunner


def azure_wrapper(func):
    """Epsagon's Azure Function wrapper."""

    @functools.wraps(func)
    def _azure_wrapper(*args, **kwargs):
        tracer.prepare()

        # Trigger event is not supported yet.

        runner = AzureFunctionRunner(time.time())
        tracer.events.append(runner)

        try:
            result = func(*args, **kwargs)
            return result
        except Exception as exception:
            runner.set_exception(exception, traceback.format_exc())
            raise
        finally:
            runner.terminate()
            tracer.send_traces()

    return _azure_wrapper
