"""
Example for Epsagon usage in Flask application.
"""

from flask import Flask
import epsagon

epsagon.init(
    token='my-secret-token',
    app_name='my-app-name',
    metadata_only=False
)


app = Flask(__name__)
epsagon.flask_wrapper(app)


@app.route('/')
def hello():
    return "Hello World!"


app.run()
