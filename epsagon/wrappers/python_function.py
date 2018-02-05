"""
Wrapper for a general python function
"""

from __future__ import absolute_import
import time
import traceback
import functools
from ..trace import tracer
from ..runners.python_function import PythonRunner


def python_wrapper(func):
    """Epsagon's general python wrapper."""

    @functools.wraps(func)
    def _python_wrapper(*args, **kwargs):
        tracer.prepare()

        runner = PythonRunner(time.time(), func, args, kwargs)
        tracer.events.append(runner)

        try:
            result = func(*args, **kwargs)
            return result

        except Exception as exception:
            tracer.add_exception(exception, traceback.format_exc())
            raise

        finally:
            runner.terminate()
            tracer.send_traces()

    return _python_wrapper
