# Epsagon Agent for Python [![Build Status](https://travis-ci.com/epsagon/epsagon-python.svg?token=wsveVqcNtBtmq6jpZfSf&branch=master)](https://travis-ci.com/epsagon/epsagon-python)

This package provides an instrumentation to Python code running on functions for collection of distributed tracing and performance monitoring.


## Installation

From your project directory:

```
$ pip install epsagon -t .

# If running in virtualenv:
$ pip install epsagon
```

More details about lambda deployments are available in the [AWS documentation](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python-how-to-create-deployment-package.html).

## Basic Usage

Simply use our decorator to report metrics:

```python
import epsagon
epsagon.init(
    token='my-secret-token',
    app_name='my-app-name',  # Optional
)

@epsagon.lambda_wrapper
def handler(event, context):
  pass
```

## Copyright

Provided under the Apache-2.0 license. See LICENSE for details.

Copyright 2017, Epsagon.
