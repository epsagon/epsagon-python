"""
Celery patcher module.
This uses the built-in Signals in Celery to get signal for every event
"""

from __future__ import absolute_import
from importlib import import_module
from ..events.celery import (
    wrap_prerun,
    wrap_postrun,
    wrap_before_publish,
    wrap_after_publish,
    wrap_retry,
    wrap_failure,
)


def patch():
    """
    Patch module.
    :return: None
    """
    signals = import_module('celery.signals')
    signals.before_task_publish.connect(wrap_before_publish, weak=False)
    signals.after_task_publish.connect(wrap_after_publish, weak=False)
    signals.task_prerun.connect(wrap_prerun, weak=False)
    signals.task_retry.connect(wrap_retry, weak=False)
    signals.task_failure.connect(wrap_failure, weak=False)
    signals.task_postrun.connect(wrap_postrun, weak=False)
