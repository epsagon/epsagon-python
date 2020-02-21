# Epsagon Instrumentation for Python
[![Build Status](https://travis-ci.com/epsagon/epsagon-python.svg?token=wsveVqcNtBtmq6jpZfSf&branch=master)](https://travis-ci.com/epsagon/epsagon-python)
[![Pyversions](https://img.shields.io/pypi/pyversions/epsagon.svg?style=flat)](https://pypi.org/project/epsagon/)
[![PypiVersions](https://img.shields.io/pypi/v/epsagon.svg)](https://pypi.org/project/epsagon/)

This package provides an instrumentation to Python code running on functions for collection of distributed tracing and performance monitoring.

- [Installation](https://github.com/epsagon/epsagon-python#installation)
- [Usage](https://github.com/epsagon/epsagon-python#usage)
  - [AWS Lambda](https://github.com/epsagon/epsagon-python#aws-lambda)
  - [Django Application](https://github.com/epsagon/epsagon-python#django-application)
  - [Flask Application](https://github.com/epsagon/epsagon-python#flask-application)
  - [Tornado Application](https://github.com/epsagon/epsagon-python#tornado-application)
  - [Generic Python](https://github.com/epsagon/epsagon-python#generic-python)
- [Custom Data](https://github.com/epsagon/epsagon-python#custom-data)
  - [Custom Labels](https://github.com/epsagon/epsagon-python#custom-labels)
  - [Custom Errors](https://github.com/epsagon/epsagon-python#custom-errors)
  - [Ignore Keys](https://github.com/epsagon/epsagon-python#ignore-keys)
- [Frameworks Integration](https://github.com/epsagon/epsagon-python#frameworks-integration)
  - [Serverless](https://github.com/epsagon/epsagon-python#serverless)
  - [Chalice](https://github.com/epsagon/epsagon-python#chalice)
  - [Zappa](https://github.com/epsagon/epsagon-python#zappa)
- [Copyright](https://github.com/epsagon/epsagon-python#copyright)


## Installation

From your project directory:

```
$ pip install epsagon
```

More details about lambda deployments are available in the [AWS documentation](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python-how-to-create-deployment-package.html).

## Usage

Make sure to add `epsagon` under your `requirements.txt` file.

### AWS Lambda

Simply use our decorator to report metrics:

```python
import epsagon
epsagon.init(
    token='my-secret-token',
    app_name='my-app-name',
    metadata_only=False,  # Optional, send more trace data
)

@epsagon.lambda_wrapper
def handler(event, context):
  pass
```

### Django Application

Add the following code to the `settings.py` file:
```python
import epsagon
epsagon.init(
    token='my-secret-token',
    app_name='my-app-name',
    metadata_only=False,  # Optional, send more trace data
)
```

Add Epsagon middleware to the application's middleware list (located in `settings.py`)
```python
MIDDLEWARE = [
    '....',
    'epsagon.wrappers.django.DjangoMiddleware',
]
```

For web frameworks: Use ignored_endpoints to blacklist specific paths and prevent Epsagon from sending a trace.
```python
import epsagon
epsagon.init(
    ...
    ignored_endpoints=['/path', '/path/to/ignore']
)
```

### Flask Application

Use the example snippet:
```python
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
```

### Tornado Application

Use the example snippet:
```python
import tornado.ioloop
import tornado.web
import epsagon

epsagon.init(
    token='my-secret-token',
    app_name='my-app-name',
    metadata_only=False
)


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write('Hello, world')


def make_app():
    return tornado.web.Application([
        (r'/', MainHandler),
    ])


if __name__ == '__main__':
    app = make_app()
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()
```

### Generic Python

Use the example snippet:
```python
import epsagon
epsagon.init(
    token='my-secret-token',
    app_name='my-app-name',
    metadata_only=False
)


@epsagon.python_wrapper
def main():
    return 'It worked!'
  
main()
```

## Custom Data

### Custom Labels

You can add custom labels to your traces. Filters can later be used for filtering
traces that contains specific labels:
```python
def handler(event, context):
    epsagon.label('key', 'value')
    epsagon.label('user_id', event['headers']['auth'])
    epsagon.label('number_of_records_parsed_successfully', 42)
```

### Custom Errors

You can manually set a trace as an error, even if handled correctly.
Please refer to the full documentation, about handling of this errors in the issues management.

```python
def handler(event, context):
    try:
        fail = 1 / 0
    except Exception as ex:
        epsagon.error(ex)
        
    # or

    if 'my_param' not in event:
        epsagon.error(ValueError('event missing my_param'))
        # or
        epsagon.error('event missing my_param')
```


### Ignore keys

You can prevent data from being sent to epsagon by filtering specific keys in initialization.
```python
import epsagon
epsagon.init(
    token='my-secret-token',
    app_name='my-app-name',
    metadata_only=False,
    keys_to_ignore=['Request Data', 'Status_Code']
)
```
## Frameworks Integration

When using any of the following integrations, make sure to add `epsagon` under your `requirements.txt` file.

### Serverless

Using Epsagon with [Serverless](https://github.com/serverless/serverless) is simple, by using the [serverless-plugin-epsagon](https://github.com/epsagon/serverless-plugin-epsagon).

### Chalice

Using Epsagon with [Chalice](https://github.com/aws/chalice) is simple, follow this example:

```python
from chalice import Chalice
import epsagon
epsagon.init(
    token='my-secret-token',
    app_name='my-app-name',
    metadata_only=False
)
app = Chalice(app_name="hello-world")


@app.route("/")
def index():
    return {"hello": "world"}

app = epsagon.chalice_wrapper(app)
```

or In S3 trigger example:
```python
from chalice import Chalice

app = Chalice(app_name="helloworld")

import epsagon
epsagon.init(
    token='my-secret-token',
    app_name='my-app-name',
    metadata_only=False
)
# Whenever an object is uploaded to 'mybucket'
# this lambda function will be invoked.

@epsagon.lambda_wrapper
@app.on_s3_event(bucket='mybucket')
def handler(event):
    print("Object uploaded for bucket: %s, key: %s"
          % (event.bucket, event.key))
```

### Zappa

Using Epsagon with [Zappa](https://github.com/Miserlou/Zappa) is simple, follow this example:

```python
from flask import Flask
from zappa.handler import lambda_handler
import epsagon

epsagon.init(
    token='my-secret-token',
    app_name='my-app-name',
    metadata_only=False
)
app = Flask(__name__)


@app.route('/')
def hello_world():
    return 'Hello, World!'


epsagon_handler = epsagon.lambda_wrapper(lambda_handler)
```

And in your `zappa_settings.json` file include the following:
```json
{
  "lambda_handler": "module.path_to.epsagon_handler"
}
```

## Copyright


Provided under the MIT license. See LICENSE for details.

Copyright 2019, Epsagon.
