"""
Wrapper for Tencent Serverless Cloud Functions.
"""

from __future__ import absolute_import
import traceback
import time
import functools
import warnings
try:
    from collections import Mapping
except: # pylint: disable=W0702
    from collections.abc import Mapping

import epsagon.trace
import epsagon.runners.tencent_function
import epsagon.wrappers.python_function
import epsagon.utils
import epsagon.runners.python_function
from epsagon.common import EpsagonWarning
from epsagon.triggers.tencent_function import TencentFunctionTriggerFactory
from .. import constants


def _add_status_code(runner, return_value):
    """
    Tries to extract the status code from the return value and add it
    as a metadata field
    :param runner: Runner event to update
    :param return_value: The return value to extract from
    """
    if isinstance(return_value, Mapping):
        status_code = return_value.get('statusCode')
        if status_code:
            runner.resource['metadata']['status_code'] = status_code


def tencent_function_wrapper(func):
    """Epsagon's Tencent SCF wrapper."""

    # avoid double instrumentation
    if getattr(func, '__instrumented__', False):
        return func

    @functools.wraps(func)
    def _tencent_function_wrapper(*args, **kwargs):
        """
        Generic SCF function wrapper
        """
        start_time = time.time()
        cold_start_duration = start_time - constants.COLD_START_TIME
        trace = epsagon.trace.trace_factory.get_or_create_trace()
        trace.prepare()

        try:
            event, context = args
        except ValueError:
            # This can happen when someone manually calls handler without
            # parameters / sends kwargs. In such case we ignore this trace.
            return func(*args, **kwargs)

        try:
            runner = epsagon.runners.tencent_function.TencentFunctionRunner(
                start_time,
                context
            )
            trace.set_runner(runner)
        # pylint: disable=W0703
        except Exception as exception:
            # Regress to python runner.
            warnings.warn(
                'SCF context is invalid, using simple python wrapper',
                EpsagonWarning
            )
            trace.add_exception(
                exception,
                traceback.format_exc()
            )
            return epsagon.wrappers.python_function.wrap_python_function(
                func,
                args,
                kwargs
            )

        if constants.COLD_START:
            runner.resource['metadata'][
                'tencent.scf.cold_start_duration'
            ] = cold_start_duration
        constants.COLD_START = False

        try:
            trace.add_event(
                TencentFunctionTriggerFactory.factory(
                    start_time,
                    event,
                    context,
                    runner
                )
            )
        # pylint: disable=W0703
        except Exception as exception:
            trace.add_exception(
                exception,
                traceback.format_exc(),
                additional_data={'event': event}
            )

        result = None
        try:
            result = func(*args, **kwargs)
            return result
        # pylint: disable=W0703
        except Exception as exception:
            runner.set_exception(
                exception,
                traceback.format_exc(),
                handled=False
            )
            raise
        finally:
            try:
                _add_status_code(runner, result)
                if not trace.metadata_only:
                    runner.resource['metadata']['tencent.scf.return_data'] = (
                        result
                    )
            # pylint: disable=W0703
            except Exception as exception:
                trace.add_exception(
                    exception,
                    traceback.format_exc(),
                )

            try:
                epsagon.trace.trace_factory.send_traces()
            # pylint: disable=W0703
            except Exception:
                epsagon.utils.print_debug('Failed to send SCF trace')

    _tencent_function_wrapper.__instrumented__ = True
    return _tencent_function_wrapper
