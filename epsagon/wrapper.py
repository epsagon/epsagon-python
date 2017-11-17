"""
Main Epsagon agent module
"""

from __future__ import absolute_import
import traceback
# TODO: Fix json->ujson (error in azure)
import json
import os

from .trace import tracer
from .runners.aws_lambda import LambdaRunner, LambdaTriggerFactory
from .runners.azure_function import AzureFunctionRunner
from .common import ErrorCode
from . import constants

# TODO: Maybe separate to different modules (under same wrappers dirs)
# TODO: Add rate limiter for trace sends


def init(token, app_name='default'):
    tracer.initialize(
        token=token,
        app_name=app_name,
    )


def lambda_wrapper(func):
    """Epsagon's Lambda wrapper."""
    def _lambda_wrapper(*args, **kwargs):
        assert tracer.token != '', 'Please initialize token'
        event, context = args

        tracer.trigger = LambdaTriggerFactory.factory(event)
        tracer.runner = LambdaRunner(event, context)
        constants.COLD_START = False

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
            tracer.runner.terminate()
            tracer.send_traces()

    return _lambda_wrapper


def azure_wrapper(func):
    """Epsagon's Azure Function wrapper."""
    def _azure_wrapper(*args, **kwargs):
        assert tracer.token != '', 'Please initialize token'
        event = json.loads(open(os.environ['req']).read())
        tracer.trigger = LambdaTriggerFactory.factory(event)
        tracer.runner = AzureFunctionRunner()

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
            tracer.runner.terminate()
            tracer.send_traces()

    return _azure_wrapper
