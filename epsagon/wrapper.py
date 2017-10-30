"""
Main Epsagon agent module
"""

from __future__ import absolute_import
import functools
import traceback

from .trace import tracer
from .runners.aws_lambda import LambdaRunner, LambdaTriggerFactory
from .common import ErrorCode


def lambda_wrapper(app_name, token):
    """Epsagon's Lambda wrapper."""
    def _lambda_decorator(func):
        @functools.wraps(func)
        def _lambda_wrapper(*args, **kwargs):
            event, context = args

            tracer.initialize(
                app_name=app_name,
                token=token
            )

            tracer.trigger = LambdaTriggerFactory.factory(event)
            tracer.runner = LambdaRunner(event, context)

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as exception:
                tracer.runner.set_error(
                    error_code=ErrorCode.EXCEPTION,
                    exception=exception,
                    traceback=traceback.format_exc()
                )
                raise exception
            finally:
                tracer.send_traces()

        return _lambda_wrapper
    return _lambda_decorator
