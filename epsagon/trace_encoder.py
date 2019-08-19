""" JSONEncoder for trace objects """

from datetime import datetime, date
import simplejson as json


class TraceEncoder(json.JSONEncoder):
    """
    An encoder for the trace json
    """

    def default(self, o):  # pylint: disable=method-hidden
        if isinstance(o, set):
            return list(o)
        if isinstance(o, (datetime, date)):
            return o.isoformat()

        output = repr(o)
        try:
            output = json.JSONEncoder.default(self, o)
        except TypeError:
            pass
        return output
