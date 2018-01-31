"""
Main Epsagon agent module
"""

from __future__ import absolute_import
import traceback
import json
import os

from .trace import tracer
from .runners.aws_lambda import LambdaRunner, LambdaTriggerFactory
from .runners.azure_function import AzureFunctionRunner
from .common import ErrorCode
from . import constants


def init(token, app_name='default'):
    tracer.initialize(
        token=token,
        app_name=app_name,
    )

#TODO: This code can be refactored (50% of the methods are the same)

def lambda_wrapper(func):
    """Epsagon's Lambda wrapper."""

    def _lambda_wrapper(*args, **kwargs):
        tracer.prepare()
        event, context = args

        try:
            tracer.events.append(LambdaTriggerFactory.factory(event))
        except Exception as exception:
            print 'Epsagon Error: Could not load trigger {}'.format(
                exception.message)

        runner = LambdaRunner(event, context)
        tracer.events.append(runner)
        constants.COLD_START = False

        try:
            result = func(*args, **kwargs)
            return result
        except Exception as exception:
            runner.set_exception(
                error_code=ErrorCode.EXCEPTION,
                exception=exception,
                traceback=traceback.format_exc()
            )
            raise exception
        finally:
            runner.terminate()
            tracer.send_traces()

    return _lambda_wrapper


def azure_wrapper(func):
    """Epsagon's Azure Function wrapper."""

    def _azure_wrapper(*args, **kwargs):
        tracer.prepare()
        event = json.loads(open(os.environ['req']).read())
        tracer.events.append(LambdaTriggerFactory.factory(event))
        runner = AzureFunctionRunner()
        tracer.events.append(runner)

        try:
            result = func(*args, **kwargs)
            return result
        except Exception as exception:
            runner.set_exception(
                error_code=ErrorCode.EXCEPTION,
                exception=exception,
                traceback=traceback.format_exc()
            )
            raise exception
        finally:
            runner.terminate()
            tracer.send_traces()

    return _azure_wrapper
