"""
Wrapper for AWS Lambda.
"""

from __future__ import absolute_import
import traceback
import time
import functools
import warnings
from uuid import uuid4

import epsagon.trace
import epsagon.runners.aws_lambda
import epsagon.triggers.aws_lambda
import epsagon.wrappers.python_function
from epsagon.wrappers.return_value import add_return_value
import epsagon.runners.python_function
from epsagon.common import EpsagonWarning
from .. import constants

STEP_DICT_NAME = 'Epsagon'


def lambda_wrapper(func):
    """Epsagon's Lambda wrapper."""

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
            return result
        # pylint: disable=W0703
        except Exception as exception:
            runner.set_exception(exception, traceback.format_exc())
            raise
        finally:
            try:
                if not trace.metadata_only:
                    add_return_value(runner, result)
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
                trace.send_traces()
            # pylint: disable=W0703
            except Exception:
                pass

    return _lambda_wrapper


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
            if isinstance(result, dict):
                # If the step functions data is not present, then this is the
                # First step.
                if STEP_DICT_NAME not in event:
                    steps_dict = {'id': str(uuid4()), 'step_num': 0}
                # Otherwise, just advance the steps number by one.
                else:
                    steps_dict = event[STEP_DICT_NAME]
                    steps_dict['step_num'] += 1

                result[STEP_DICT_NAME] = steps_dict
                runner.add_step_data(steps_dict)
            return result
        # pylint: disable=W0703
        except Exception as exception:
            runner.set_exception(exception, traceback.format_exc())
            raise
        finally:
            try:
                if not trace.metadata_only:
                    add_return_value(runner, result)
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
                trace.send_traces()
            # pylint: disable=W0703
            except Exception:
                pass

    return _lambda_wrapper
