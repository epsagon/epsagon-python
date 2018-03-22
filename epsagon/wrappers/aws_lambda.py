"""
Wrapper for AWS Lambda.
"""

from __future__ import absolute_import
import traceback
import time
import functools
from uuid import uuid4

import epsagon.trace
import epsagon.runners.aws_lambda
import epsagon.triggers.aws_lambda
from .. import constants

STEP_DICT_NAME = 'Epsagon'


def lambda_wrapper(func):
    """Epsagon's Lambda wrapper."""

    @functools.wraps(func)
    def _lambda_wrapper(*args, **kwargs):
        epsagon.trace.tracer.prepare()
        event, context = args

        try:
            epsagon.trace.tracer.events.append(
                epsagon.triggers.aws_lambda.LambdaTriggerFactory.factory(
                    time.time(),
                    event,
                    context
                )
            )
        # pylint: disable=W0703
        except Exception as exception:
            epsagon.trace.tracer.add_exception(
                exception,
                traceback.format_exc()
            )

        runner = epsagon.runners.aws_lambda.LambdaRunner(time.time(), context)
        constants.COLD_START = False

        try:
            result = func(*args, **kwargs)
            return result
        except Exception as exception:
            runner.set_exception(exception, traceback.format_exc())
            raise
        finally:
            epsagon.trace.tracer.add_event(runner)
            epsagon.trace.tracer.send_traces()

    return _lambda_wrapper


def step_lambda_wrapper(func):
    """Epsagon's Step Lambda wrapper."""

    @functools.wraps(func)
    def _lambda_wrapper(*args, **kwargs):
        epsagon.trace.tracer.prepare()
        event, context = args

        try:
            epsagon.trace.tracer.events.append(
                epsagon.triggers.aws_lambda.LambdaTriggerFactory.factory(
                    time.time(),
                    event,
                    context
                )
            )
        # pylint: disable=W0703
        except Exception as exception:
            epsagon.trace.tracer.add_exception(
                exception,
                traceback.format_exc()
            )

        runner = epsagon.runners.aws_lambda.LambdaRunner(time.time(), context)
        constants.COLD_START = False

        try:
            result = func(*args, **kwargs)
            # Add step functions data only if the result is a dictionary.
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
            return result
        except Exception as exception:
            runner.set_exception(exception, traceback.format_exc())
            raise
        finally:
            epsagon.trace.tracer.add_event(runner)
            epsagon.trace.tracer.send_traces()

    return _lambda_wrapper
