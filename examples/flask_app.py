"""
Example for a basic flask app
"""

import epsagon
from flask import Flask
import logging
app = Flask(__name__)

epsagon.init(
    token='my-secret-token',
    app_name='my-app-name',
    metadata_only=False,
    debug=False,
)

epsagon.flask_wrapper(app)


@app.route('/')
def root():
    logging.error('hello')
    logging.error('hello2')
    return 'It worked!'


@app.route('/something')
def something():
    logging.error('hello3')


if __name__ == '__main__':
    app.run(threaded=True)
