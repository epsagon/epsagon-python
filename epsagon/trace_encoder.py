""" JSONEncoder for trace objects """

from datetime import datetime, date
import json


class TraceEncoder(json.JSONEncoder):
    """
    An encoder for the trace json
    """

    def default(self, o):  # pylint: disable=method-hidden
        if isinstance(o, set):
            return list(o)
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        if isinstance(o, bytes):
            return o.decode('utf-8', errors='ignore')

        output = repr(o)
        try:
            output = json.JSONEncoder.default(self, o)
        except TypeError:
            pass
        return output
