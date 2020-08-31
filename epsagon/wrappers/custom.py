"""
A helper wrapper to measure internal functions duration
"""

from __future__ import absolute_import
import time
import functools
from ..trace import trace_factory


def measure(func):
    """A decorator to measure internal functions duration using labels."""

    @functools.wraps(func)
    def _measure(*args, **kwargs):
        """
        Creating a label based on the function name
        with the duration in seconds.
        """
        start_time = time.time()
        result = func(*args, **kwargs)
        trace_factory.add_label(
            '{}_duration'.format(func.__name__),
            float('{:.3f}'.format(time.time() - start_time))
        )
        return result
    return _measure
