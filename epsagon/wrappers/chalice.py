"""
Wrapper for AWS Lambda in Chalice environment.
"""

from __future__ import absolute_import
from epsagon.wrappers import lambda_wrapper


class ChaliceWrapper:
    """
    Class handles wrapping Chalice app.
    In call we expect an invocation to come, and in getattr we allow `app.attr`
    calls.
    """
    def __init__(self, app):
        self.app = app

    def __getattr__(self, item):
        return getattr(self.app, item)

    def __call__(self, *args, **kwargs):
        return lambda_wrapper(self.app)(*args, **kwargs)


def chalice_wrapper(app):
    """
    Chalice wrapper
    :param app: Chalice app
    :return: ChaliceWrapper
    """
    return ChaliceWrapper(app)
