"""
Wrapper for AWS Lambda.
"""

from __future__ import absolute_import
import traceback
import time
import copy
import functools
import warnings
import collections
from uuid import uuid4

import epsagon.trace
import epsagon.runners.aws_lambda
import epsagon.triggers.aws_lambda
import epsagon.wrappers.python_function
import epsagon.utils
from epsagon.constants import STEP_DICT_NAME, EPSAGON_EVENT_ID_KEY
import epsagon.runners.python_function
from epsagon.common import EpsagonWarning
from .. import constants


def _add_status_code(runner, return_value):
    """
    Tries to extract the status code from the return value and add it
    as a metadata field
    :param runner: Runner event to update
    :param return_value: The return value to extract from
    """
    if isinstance(return_value, collections.Mapping):
        status_code = return_value.get('statusCode')
        if status_code:
            runner.resource['metadata']['status_code'] = status_code


def lambda_wrapper(func):
    """Epsagon's Lambda wrapper."""

    # avoid double instrumentation
    if getattr(func, '__instrumented__', False):
        return func

    @functools.wraps(func)
    def _lambda_wrapper(*args, **kwargs):
        """
        Generic Lambda function wrapper
        """
        trace = epsagon.trace.trace_factory.get_or_create_trace()
        trace.prepare()

        try:
            event, context = args
        except ValueError:
            # This can happen when someone manually calls handler without
            # parameters / sends kwargs. In such case we ignore this trace.
            return func(*args, **kwargs)

        try:
            runner = epsagon.runners.aws_lambda.LambdaRunner(
                time.time(),
                context
            )
            trace.set_runner(runner)
        # pylint: disable=W0703
        except Exception as exception:
            # Regress to python runner.
            warnings.warn(
                'Lambda context is invalid, using simple python wrapper',
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

        constants.COLD_START = False

        try:
            trace.add_event(
                epsagon.triggers.aws_lambda.LambdaTriggerFactory.factory(
                    time.time(),
                    event,
                    context
                )
            )
        # pylint: disable=W0703
        except Exception as exception:
            trace.add_exception(
                exception,
                traceback.format_exc(),
                additional_data={'event': event}
            )

        if not trace.disable_timeout_send:
            trace.set_timeout_handler(context)

        result = None
        try:
            result = func(*args, **kwargs)
            if trace.propagate_lambda_id and isinstance(result, dict):
                result[EPSAGON_EVENT_ID_KEY] = runner.event_id
                runner.resource['metadata']['propagation_enabled'] = True
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
                    runner.resource['metadata']['return_value'] = result
            # pylint: disable=W0703
            except Exception as exception:
                trace.add_exception(
                    exception,
                    traceback.format_exc(),
                )
            try:
                if not trace.disable_timeout_send:
                    epsagon.trace.Trace.reset_timeout_handler()
            # pylint: disable=W0703
            except Exception:
                pass
            try:
                epsagon.trace.trace_factory.send_traces()
            # pylint: disable=W0703
            except Exception:
                pass

    _lambda_wrapper.__instrumented__ = True
    return _lambda_wrapper


# pylint: disable=too-many-statements
def step_lambda_wrapper(func):
    """Epsagon's Step Lambda wrapper."""

    @functools.wraps(func)
    def _lambda_wrapper(*args, **kwargs):
        """
        Generic Step Function wrapper
        """
        trace = epsagon.trace.trace_factory.get_or_create_trace()
        trace.prepare()

        try:
            event, context = args
        except ValueError:
            # This can happen when someone manually calls handler without
            # parameters / sends kwargs. In such case we ignore this trace.
            return func(*args, **kwargs)

        try:
            runner = epsagon.runners.aws_lambda.StepLambdaRunner(
                time.time(),
                context
            )
            trace.set_runner(runner)
        # pylint: disable=W0703
        except Exception as exception:
            # Regress to python runner.
            warnings.warn(
                'Lambda context is invalid, using simple python wrapper',
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

        constants.COLD_START = False

        try:
            trace.add_event(
                epsagon.triggers.aws_lambda.LambdaTriggerFactory.factory(
                    time.time(),
                    event,
                    context
                )
            )
        # pylint: disable=W0703
        except Exception as exception:
            trace.add_exception(
                exception,
                traceback.format_exc(),
                additional_data={'event': event}
            )

        trace.set_timeout_handler(context)

        result = None
        try:
            result = func(*args, **kwargs)
            steps_data = epsagon.utils.find_in_object(
                event,
                STEP_DICT_NAME
            )

            if isinstance(result, dict):
                epsagon.utils.print_debug(
                    'Step function result type is dict, steps_data={}'.format(
                        steps_data
                    )
                )
                # If the step functions data is not present, then this is the
                # First step.
                if steps_data is None:
                    epsagon.utils.print_debug(
                        'Could not find existing steps data'
                    )
                    steps_dict = {'id': str(uuid4()), 'step_num': 0}
                    path = []
                # Otherwise, just advance the steps number by one.
                else:
                    # don't change trigger data
                    steps_dict, path = steps_data
                    steps_dict = copy.deepcopy(steps_dict)
                    if 'step_num' in steps_dict:
                        steps_dict['step_num'] += 1
                        epsagon.utils.print_debug(
                            'Steps data found, new dict={}'.format(steps_dict)
                        )
                    else:
                        steps_dict = {'id': str(uuid4()), 'step_num': 0}
                        epsagon.utils.print_debug(
                            'Steps data not found, new dict={}'.format(
                                steps_dict
                            )
                        )

                result_path = result
                # Tries to inject the steps data in the configured
                # or same path where it was found
                if isinstance(trace.step_dict_output_path, list):
                    path = trace.step_dict_output_path
                try:
                    for sub_path in path:
                        result_path = result_path.get(sub_path)
                except Exception as exception:  # pylint: disable=broad-except
                    epsagon.utils.print_debug(
                        'Could not put steps in path={}'.format(path)
                    )
                if result_path:
                    epsagon.utils.print_debug(
                        'Adding steps dict to result_path={}'.format(
                            result_path
                        )
                    )
                    result_path[STEP_DICT_NAME] = steps_dict
                else:
                    epsagon.utils.print_debug(
                        'Adding steps dict to root result'
                    )
                    result[STEP_DICT_NAME] = steps_dict

                runner.add_step_data(steps_dict)
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
                    runner.resource['metadata']['return_value'] = (
                        copy.deepcopy(result)
                    )
            # pylint: disable=W0703
            except Exception as exception:
                trace.add_exception(
                    exception,
                    traceback.format_exc(),
                )
            try:
                epsagon.trace.Trace.reset_timeout_handler()
            # pylint: disable=W0703
            except Exception:
                pass
            try:
                epsagon.trace.trace_factory.send_traces()
            # pylint: disable=W0703
            except Exception:
                pass

    return _lambda_wrapper
