"""
Wrapper for a general python function
"""

from __future__ import absolute_import
import time
import traceback
import functools
import epsagon.trace
import epsagon.runners.python_function
from epsagon.wrappers.return_value import add_return_value
from epsagon import constants


def wrap_python_function(func, args, kwargs):
    """
    Wrap a python function call with a simple python wrapper. Used as default
    when wrapping with other wrappers is impossible.
    NOTE: this function does not prepare the tracer (clears the previous run)
    :param func: The function to wrap.
    :param args: The arguments to the function.
    :param kwargs: The keyword arguments to the function.
    :return: The function's result.
    """
    try:
        runner = epsagon.runners.python_function.PythonRunner(
            time.time(),
            func,
            args,
            kwargs
        )
    # pylint: disable=W0703
    except Exception:
        # If we failed, just call the user's function. Nothing more to do.
        return func(*args, **kwargs)

    # settings in case we are in a lambda and context is None
    constants.COLD_START = False

    result = None
    try:
        result = func(*args, **kwargs)
        return result
    # pylint: disable=W0703
    except Exception as exception:
        runner.set_exception(exception, traceback.format_exc())
        raise
    finally:
        try:
            if not epsagon.trace.tracer.metadata_only:
                add_return_value(runner, result)
        # pylint: disable=W0703
        except Exception as exception:
            epsagon.trace.tracer.add_exception(
                exception,
                traceback.format_exc(),
            )
        try:
            epsagon.trace.tracer.add_event(runner)
            epsagon.trace.tracer.send_traces()
        # pylint: disable=W0703
        except Exception:
            pass


def python_wrapper(func):
    """Epsagon's general python wrapper."""

    @functools.wraps(func)
    def _python_wrapper(*args, **kwargs):
        epsagon.trace.tracer.prepare()
        return wrap_python_function(func, args, kwargs)

    return _python_wrapper
