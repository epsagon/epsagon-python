import time
import json
import requests


events = []
transaction_id = None
function_name = None
app_name = None
token = None
TRACES_URL = 'http://api.epsagon.com/event'


class Event(object):
    """
    Represents agent's event
    """

    ER_OK = 0
    ER_EXCEPTION = 1

    def __init__(self, event_id, event_type, service_type, service_name, duration,
                 end_reason, metadata=None, timestamp=None):
        self.event_id = event_id
        self.event_type = event_type
        self.service_type = service_type
        self.service_name = service_name
        self.duration = duration
        self.end_reason = end_reason
        self.metadata = metadata
        if metadata is None:
            self.metadata = {}
        self.timestamp = timestamp
        if timestamp is None:
            self.timestamp = time.time()

    def get_dict(self):
        global transaction_id, function_name, app_name
        event_json = {
            'id': self.event_id,
            'transaction_id': transaction_id,
            'function_name': function_name,
            'app_name': app_name,
            'token': token,
            'event_type': self.event_type,
            'service_type': self.service_type,
            'service_name': self.service_name,
            'timestamp': str(self.timestamp),
            'duration': str(self.duration),
            'end_reason': self.end_reason,
            'metadata': self.metadata
        }
        return event_json


def send_to_server():
    global events
    events_json = json.dumps([event.get_dict() for event in events])
    requests.post(TRACES_URL, data=events_json)
    events = []
