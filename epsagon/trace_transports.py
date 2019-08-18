"""trace transport layers"""

import json
import logging
import requests
from epsagon.constants import SEND_TIMEOUT
from epsagon.trace_encoder import TraceEncoder


def to_json(obj):
    return json.dumps(obj, cls=TraceEncoder, encoding='latin1')


class NoneTransport(object):
    @classmethod
    def send(cls, _):
        logging.error('trace sent using NoneTransport, configure a transport')


class LogTransport(object):
    """ send traces by logging them """

    def __init__(self, token):
        self.token = token

    def send(self, trace):
        trace_log = {'messageType': 'trace',
                     'token': self.token,
                     'trace': trace.to_dict()}
        print(to_json(trace_log))  # using print to avoid logging level issues


class HTTPTransport(object):
    """ send traces using http request """

    def __init__(self, dest, token):
        self.dest = dest
        self.token = token
        self.timeout = SEND_TIMEOUT
        self.session = requests.Session()

    def send(self, trace):
        headers = {'Authorization': f'Bearer {self.token}'}
        self.session.post(url=self.dest,
                          data=to_json(trace.to_dict()),
                          headers=headers,
                          timeout=self.timeout)
