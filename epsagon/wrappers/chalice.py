"""
Wrapper for AWS Lambda in Chalice environment.
"""

from __future__ import absolute_import
from .aws_lambda import lambda_wrapper


class ChaliceWrapper(object):
    """
    Class handles wrapping Chalice app.
    In call we expect an invocation to come, and in getattr we allow `app.attr`
    calls.
    """
    def __init__(self, app):
        self._app = app

    def __getattr__(self, item):
        return getattr(self._app, item)

    def __setattr__(self, name, value):
        if name == '__class__' and value.__name__ == 'LocalChalice':
            # In local runs, the class is being changed to `LocalChalice`,
            # So we do that to preserve the same behaviour
            value.__getattr__ = self.__getattr__
        super(ChaliceWrapper, self).__setattr__(name, value)

    def __call__(self, *args, **kwargs):
        return lambda_wrapper(self._app)(*args, **kwargs)


def chalice_wrapper(app):
    """
    Chalice wrapper
    :param app: Chalice app
    :return: ChaliceWrapper
    """
    return ChaliceWrapper(app)
