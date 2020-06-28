"""
Wrapper for Azure Function.
"""

from __future__ import absolute_import
import time
import traceback
import warnings
import functools
from ..trace import trace_factory
from ..runners.azure_function import AzureFunctionRunner
from ..triggers.azure_function import AzureTriggerFactory
from ..common import EpsagonWarning


def azure_wrapper(func):
    """Epsagon's Azure Function wrapper."""

    @functools.wraps(func)
    def _azure_wrapper(*args, **kwargs):
        """
        general Azure function wrapper
        """
        trace = trace_factory.get_or_create_trace()
        trace.prepare()

        import logging
        logging.info('kwargs = %s', kwargs)

        context = kwargs.get('context')
        logging.info('context = %s', context)
        if not context:
            return func(*args, **kwargs)

        # Create Runner
        # try:
        runner = AzureFunctionRunner(time.time(), context)
        logging.info('runner = %s', runner)
        trace.set_runner(runner)
        # except Exception as exception:  # pylint: disable=broad-except
        #     warnings.warn(
        #         'Could not create Azure Function runner',
        #         EpsagonWarning
        #     )
        #     return func(*args, **kwargs)

        # Create Trigger
        # try:

        logging.info('before trigger')
        azure_trigger = AzureTriggerFactory.factory(
            time.time(),
            kwargs
        )
        if azure_trigger:
            logging.info('in trigger = %s', azure_trigger)
            trace.add_event(azure_trigger)
        logging.info('after trigger')
        # except Exception as exception:  # pylint: disable=broad-except
        #     warnings.warn(
        #         'Could not create Azure Function runner',
        #         EpsagonWarning
        #     )
        #     return func(*args, **kwargs)


        try:
            result = func(*args, **kwargs)
            logging.info('after result')
            return result
        except Exception as exception:
            runner.set_exception(exception, traceback.format_exc())
            raise
        finally:
            runner.terminate()
            trace_factory.send_traces()

    return _azure_wrapper
