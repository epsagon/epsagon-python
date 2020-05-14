"""
Example for custom labels usage in AWS Lambda function.
"""

import epsagon
from flask import Flask
app = Flask(__name__)

epsagon.init(
    token='my-secret-token',
    app_name='my-app-name',
    metadata_only=False
)

epsagon.flask_wrapper(app)


@app.route('/')
def root():
    return 'It worked!'


if __name__ == '__main__':
    app.run()
