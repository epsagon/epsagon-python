"""trace transport layers"""

import os
import base64
import logging
import json
import urllib3
from epsagon.constants import SEND_TIMEOUT
from epsagon.trace_encoder import TraceEncoder


def to_json(obj):
    return json.dumps(obj, cls=TraceEncoder, ensure_ascii=True)


class NoneTransport(object):
    @classmethod
    def send(cls, _):
        logging.error('trace sent using NoneTransport, configure a transport')


class LogTransport(object):
    """ send traces by logging them """

    @staticmethod
    def send(trace):
        trace_json = to_json(trace.to_dict())
        trace_message = base64.b64encode(
            trace_json.encode('utf-8')
        ).decode('utf-8')

        # pylint: disable=superfluous-parens
        print('EPSAGON_TRACE: {}'.format(trace_message))


class HTTPTransport(object):
    """ send traces using http request """

    def __init__(self, dest, token):
        self.dest = dest
        self.token = token
        self.timeout = SEND_TIMEOUT
        self.session = urllib3.PoolManager(
            cert_reqs='CERT_REQUIRED',
            ca_certs=os.path.join(os.path.dirname(__file__), 'cacert.pem'),
            headers={
                'Authorization': 'Bearer {}'.format(self.token),
                'Content-Type': 'application/json'
            },
            # max size of reusable connections
            maxsize=5
        )

    def send(self, trace):
        self.session.request(
            'POST',
            self.dest,
            body=to_json(trace.to_dict()),
            timeout=self.timeout,
            retries=False
        )
