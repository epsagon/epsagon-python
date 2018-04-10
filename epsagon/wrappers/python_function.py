"""
Wrapper for a general python function
"""

from __future__ import absolute_import
import time
import traceback
import functools
from ..trace import tracer
from ..runners.python_function import PythonRunner
from epsagon import constants


def wrap_python_function(func, args, kwargs):
    """
    Wrap a python function call with a simple python wrapper. Used as default
    when wrapping with other wrappers is impossible.
    :param func: The function to wrap.
    :param args: The arguments to the function.
    :param kwargs: The keyword arguments to the function.
    :return: The function's result.
    """
    tracer.prepare()
    runner = PythonRunner(time.time(), func, args, kwargs)

    # settings in case we are in a lambda and context is None
    constants.COLD_START = False
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


def python_wrapper(func):
    """Epsagon's general python wrapper."""

    @functools.wraps(func)
    def _python_wrapper(*args, **kwargs):
        wrap_python_function(func, args, kwargs)

    return _python_wrapper
