"""
Wrapper for Google Function.
"""

from __future__ import absolute_import
import traceback
import time
import functools
import warnings
import epsagon.trace
import epsagon.wrappers.python_function
from epsagon.common import EpsagonWarning
from ..runners.gcp_function import GoogleFunctionRunner
from .. import constants


def gcp_wrapper(func):
    """Epsagon's GCP wrapper."""

    @functools.wraps(func)
    def _gcp_wrapper(*args, **kwargs):
        """
        Generic google function wrapper
        """
        trace = epsagon.trace.trace_factory.get_or_create_trace()
        trace.prepare()

        try:
            runner = GoogleFunctionRunner(
                time.time(),
            )
        # pylint: disable=W0703
        except Exception as exception:
            # Regress to python runner.
            warnings.warn(
                'GCP environment is invalid, using simple python wrapper',
                EpsagonWarning
            )
            trace.add_exception(exception, traceback.format_exc())
            return epsagon.wrappers.python_function.wrap_python_function(
                func,
                args,
                kwargs
            )

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
                if not trace.metadata_only:
                    runner.resource['metadata']['return_value'] = result
            # pylint: disable=W0703
            except Exception as exception:
                trace.add_exception(exception, traceback.format_exc())
            try:
                trace.add_event(runner)
                epsagon.trace.trace_factory.send_traces()
            # pylint: disable=W0703
            except Exception:
                pass

    return _gcp_wrapper
