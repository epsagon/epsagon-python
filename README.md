# Epsagon Instrumentation for Python
[![Build Status](https://travis-ci.com/epsagon/epsagon-python.svg?token=wsveVqcNtBtmq6jpZfSf&branch=master)](https://travis-ci.com/epsagon/epsagon-python)
[![Pyversions](https://img.shields.io/pypi/pyversions/epsagon.svg?style=flat)](https://pypi.org/project/epsagon/)
[![PypiVersions](https://img.shields.io/pypi/v/epsagon.svg)](https://pypi.org/project/epsagon/)

This package provides an instrumentation to Python code running on functions for collection of distributed tracing and performance monitoring.


## Installation

From your project directory:

```
$ pip install epsagon
```

More details about lambda deployments are available in the [AWS documentation](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python-how-to-create-deployment-package.html).

## Basic Usage

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

## Custom labels

You can add custom labels to your traces. Filters can later be used for filtering
traces that contains specific labels:
```python
@epsagon.lambda_wrapper
def handler(event, context):
  epsagon.label('label', 'something_to_filter_afterwards')
  epsagon.label('number_of_records_parsed_successfully', 42)
  pass
```

## Set Error

Set a custom error, maybe without even failing the function:
```python
@epsagon.lambda_wrapper
def handler(event, context):
  if 'my_param' not in event:
      epsagon.error(ValueError('event missing my_param'))
  pass
```

## Copyright

Provided under the MIT license. See LICENSE for details.

Copyright 2019, Epsagon.
