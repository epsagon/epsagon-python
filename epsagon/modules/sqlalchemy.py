"""
sqlalchemy patcher module.
"""

from __future__ import absolute_import
import time
import wrapt
import traceback
import sqlalchemy.event
from epsagon.trace import tracer
from ..events.sqlalchemy import SQLAlchemyEventFactory


class EngineWrapper(object):

    def __init__(self, engine):
        self.engine = engine
        self.start_time = None

        sqlalchemy.event.listen(engine, 'before_cursor_execute', self._before_cur_execute)
        sqlalchemy.event.listen(engine, 'after_cursor_execute', self._after_cur_execute)
        sqlalchemy.event.listen(engine, 'dbapi_error', self._after_cur_execute)

    def _before_cur_execute(self, conn, cursor, statement, *args):
        self.start_time = time.time()

    def _after_cur_execute(self, conn, cursor, statement, *args):
        if self.start_time is not None:
            SQLAlchemyEventFactory.create_event(
                self.engine,
                cursor,
                statement,
                args,
                self.start_time,
            )

        self.start_time = None


def _create_engine_wrapper(wrapped, instance, args, kwargs):
    """
    Commit wrapper for sqlalchemy instrumentation.
    :param wrapped: wrapt's wrapped
    :param instance: wrapt's instance
    :param args: wrapt's args
    :param kwargs: wrapt's kwargs
    :return: None
    """

    engine = wrapped(*args, **kwargs)

    try:
        EngineWrapper(engine)
    except Exception as e:
        tracer.add_exception(e, traceback.format_exc())
    finally:
        return engine


def patch():
    """
    Patch module.
    :return: None
    """

    wrapt.wrap_function_wrapper(
        'sqlalchemy',
        'create_engine',
        _create_engine_wrapper
    )

    wrapt.wrap_function_wrapper(
        'sqlalchemy.engine',
        'create_engine',
        _create_engine_wrapper
    )
