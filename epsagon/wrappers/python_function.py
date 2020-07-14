"""
Wrapper for a general python function
"""

from __future__ import absolute_import
import time
import traceback
import functools
import epsagon.trace
import epsagon.runners.python_function
from epsagon.utils import collect_container_metadata
from epsagon import constants


def wrap_python_function(func, args, kwargs, name=None):
    """
    Wrap a python function call with a simple python wrapper. Used as default
    when wrapping with other wrappers is impossible.
    NOTE: this function does not prepare the tracer (clears the previous run)
    :param func: The function to wrap.
    :param args: The arguments to the function.
    :param kwargs: The keyword arguments to the function.
    :param name: Resource name for the runner
    :return: The function's result.
    """
    try:
        runner = epsagon.runners.python_function.PythonRunner(
            time.time(),
            func,
            args,
            kwargs,
            name=name
        )
        epsagon.trace.trace_factory.set_runner(runner)

        # Collect metadata in case this is a container.
        collect_container_metadata(runner.resource['metadata'])

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
            runner.add_json_field('python.function.return_value', result)
        # pylint: disable=W0703
        except Exception as exception:
            epsagon.trace.trace_factory.add_exception(
                exception,
                traceback.format_exc(),
            )
        try:
            epsagon.trace.trace_factory.send_traces()
        # pylint: disable=W0703
        except Exception:
            pass


def python_wrapper(*args, **kwargs):
    """
    Epsagon's general Python wrapper.

    Receives optional keyword arg 'name': used to identify this resource in
        the application (defaults to function name).

    Options for using:
    -   @python_wrapper(name='my-resource')
        def my_function(params):
            ...

    -   @python_wrapper()
        def my_function(params):
            ...

    -   @python_wrapper
        def my_function(params):
            ...

    NOTE: Should not be used for two functions in the same stack trace, or when
          running under a traced context (e.g. AWS Lambda, HTTP frameworks, etc)
    """
    name = kwargs.get('name')

    def _inner_wrapper(func):

        @functools.wraps(func)
        def _python_wrapper(*args, **kwargs):
            epsagon.trace.trace_factory.get_or_create_trace().prepare()
            return wrap_python_function(func, args, kwargs, name=name)

        return _python_wrapper

    if len(args) == 1 and callable(args[0]):
        return _inner_wrapper(args[0])

    return _inner_wrapper
