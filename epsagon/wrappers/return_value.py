"""
Collect wrapped function return value
"""
import json
import decimal


FAILED_TO_SERIALIZE_MESSAGE = 'Failed to serialize returned object to JSON'
MAX_SIZE_LIMIT = 1024 * 3


# pylint: disable=invalid-name
class _number_str(float):
    """ Taken from `bootstrap.py` of AWS Lambda Python runtime """
    # pylint: disable=super-init-not-called
    def __init__(self, o):
        self.o = o

    def __repr__(self):
        return str(self.o)


def _decimal_serializer(o):
    """ Taken from `bootstrap.py` of AWS Lambda Python runtime """
    if isinstance(o, decimal.Decimal):
        return _number_str(o)
    raise TypeError(repr(o) + ' is not JSON serializable')


def add_return_value(runner, return_value):
    """
    Add JSON serialized return value to given runner.
    The serialization is the same as in AWS Lambda runtime
    :param runner: Runner event to update
    :param return_value: The return value to add
    """
    try:
        json_value = json.dumps(return_value, default=_decimal_serializer)
    # pylint: disable=W0703
    except Exception:
        json_value = FAILED_TO_SERIALIZE_MESSAGE

    runner.resource['metadata']['return_value'] = json_value[:MAX_SIZE_LIMIT]
