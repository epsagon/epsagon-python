# Epsagon Agent for Python

This package provides a Python object to send telemetry to the IOpipe platform for application performance monitoring, analytics, and distributed tracing.

Explanation on trace, event...


## Installation

From your project directory:

```
$ pip install epsagon -t .

# If running in virtualenv:
$ pip install epsagon
```

Installation of the requests library is necessary for local dev/test, but not
when running on AWS Lambda as this library is part of the default environment
via the botocore library.

More details about lambda deployments are available in the [AWS documentation](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python-how-to-create-deployment-package.html).

## Basic Usage

Simply use our decorator to report metrics:

```python
import epsagon

@epsagon.lambda_wrapper(app_name='my_app', token='SCERET_TOKEN')
def handler(event, context):
  pass
```

## Configuration

The following may be set as kwargs to the Epsagon wrapper:

- app_name: name of your application
- token: secret token provided from epsagon
- is_active: whether to active or not

### Disabling Epsagon

```python
import epsagon

@epsagon.lambda_wrapper(app_name='my_app', token='SCERET_TOKEN', is_active=False)
def handler(event, context):
  pass
```

## Copyright

Provided under the Apache-2.0 license. See LICENSE for details.

Copyright 2017, Epsagon.
