"""Common objects"""


class ErrorCode(object):
    """
    Error codes enum
    """
    OK = 0
    ERROR = 1
    EXCEPTION = 2
    TIMEOUT = 3


class EpsagonWarning(Warning):
    """
    An Epsagon warning.
    """
