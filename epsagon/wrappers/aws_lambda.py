"""
Wrapper for AWS Lambda.
"""

from __future__ import absolute_import
import traceback
import time
import functools
import epsagon.trace
import epsagon.runners.aws_lambda
import epsagon.triggers.aws_lambda
from .. import constants


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
            epsagon.trace.tracer.add_exception(exception,
                                               traceback.format_exc())

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
