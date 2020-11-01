<p align="center">
  <a href="https://epsagon.com" target="_blank" align="center">
    <img src="https://cdn2.hubspot.net/hubfs/4636301/Positive%20RGB_Logo%20Horizontal%20-01.svg" width="300">
  </a>
  <br />
</p>

[![Build Status](https://travis-ci.com/epsagon/epsagon-python.svg?token=wsveVqcNtBtmq6jpZfSf&branch=master)](https://travis-ci.com/epsagon/epsagon-python)
[![Pyversions](https://img.shields.io/pypi/pyversions/epsagon.svg?style=flat)](https://pypi.org/project/epsagon/)
[![PypiVersions](https://img.shields.io/pypi/v/epsagon.svg)](https://pypi.org/project/epsagon/)

# Epsagon Tracing for Python

This package provides tracing to Python applications for the collection of distributed tracing and performance metrics in [Epsagon](https://app.epsagon.com/?utm_source=github).


## Contents

- [Installation](#installation)
- [Usage](#usage)
  - [Auto-tracing](#auto-tracing)
  - [Calling the SDK](#calling-the-sdk)
  - [Tagging Traces](#tagging-traces)
  - [Measuring Function Duration](#measuring-function-duration)
  - [Custom Errors](#custom-errors)
  - [Filter Sensitive Data](#filter-sensitive-data)
  - [Ignore Endpoints](#ignore-endpoints)
  - [Trace URL](#trace-url)
- [Frameworks](#frameworks)
- [Integrations](#integrations)
- [Configuration](#configuration)
- [Getting Help](#getting-help)
- [Opening Issues](#opening-issues)
- [License](#license)


## Installation

To install Epsagon, simply run:
```sh
pip install -U epsagon
```

## Usage

### Auto-tracing

The simplest way to get started is to run your python command with the following environment variable:
```sh
export EPSAGON_TOKEN=<epsagon-token>
export EPSAGON_APP_NAME=<app-name-stage>
export AUTOWRAPT_BOOTSTRAP=epsagon
<python command>
```

For example:
```sh
export EPSAGON_TOKEN=<your-token>
export EPSAGON_APP_NAME=django-prod
export AUTOWRAPT_BOOTSTRAP=epsagon
python app.py
```

When using inside a `Dockerfile`, you can use `ENV` instead of `export`.

You can see the list of auto-tracing [supported frameworks](#frameworks)

### Calling the SDK

Another simple alternative is to copy the snippet into your code:
```python
import epsagon
epsagon.init(
    token='epsagon-token',
    app_name='app-name-stage',
    metadata_only=False,
)
```

To run on your framework please refer to [supported frameworks](#frameworks)


### Tagging Traces

You can add custom tags to your traces, for easier filtering and aggregations.

Add the following call inside your code:
```python
epsagon.label('key', 'value')
epsagon.label('user_id', user_id)
```

You can also use it to ship custom metrics:
```python
epsagon.label('key', 'metric')
epsagon.label('items_in_cart', items_in_cart)
```

Valid types are `string`, `bool`, `int` and `float`.
In some [frameworks](#frameworks) tagging can be done in different ways.

### Measuring Function Duration

You can measure internal functions duration by using the `@epsagon.measure` decorator. For example:
```python
@epsagon.measure
def heavy_calculation():
    # Code...
```

This will ship another metric label to epsagon where the `key=heavy_calculation_duration` and the value will be the actual duration, in seconds.
You'll be able to see this label in the trace search, visualize it over time, and generate alerts based on this metric.

### Custom Errors

You can set a trace as an error (although handled correctly) to get an alert or just follow it on the dashboard.

Add the following call inside your code:
```python
try:
    fail = 1 / 0
except Exception as ex:
    epsagon.error(ex)

# Or manually specify Exception object
epsagon.error(Exception('My custom error'))
```

In some [frameworks](#frameworks) custom errors can be declared in different ways.

### Filter Sensitive Data

You can pass a list of sensitive properties and hostnames and they will be filtered out from the traces:

```python
epsagon.init(
    token='epsagon-token',
    app_name='app-name-stage',
    metadata_only=False,
    keys_to_ignore=['password', 'user_name'],
    url_patterns_to_ignore=['example.com', 'auth.com']
)
```

Or specify keys that are allowed:

```python
epsagon.init(
    token='epsagon-token',
    app_name='app-name-stage',
    metadata_only=False,
    keys_to_allow=['Request Data', 'Status_Code'],
)
```

The `keys_to_ignore` and `keys_to_allow` properties can contain strings (will perform a loose match, so that `First Name` also matches `first_name`).
Also, you can set `url_patterns_to_ignore` to ignore HTTP calls to specific domains.


### Ignore Endpoints

You can ignore certain incoming requests by specifying endpoints:
```python
epsagon.init(
    token='epsagon-token',
    app_name='app-name-stage',
    metadata_only=False,
    ignored_endpoints=['/healthcheck'],
)
```

### Trace URL

You can get the Epsagon dashboard URL for the current trace, using the following:
```python
import epsagon

# Inside some endpoint or function
print('Epsagon trace URL:', epsagon.get_trace_url())
```

This can be useful to have an easy access the trace from different platforms.

## Frameworks

The following frameworks are supported by Epsagon:

|Framework                               |Supported Version          |Auto-tracing Supported                               |
|----------------------------------------|---------------------------|-----------------------------------------------------|
|[AWS Lambda](#aws-lambda)               |All                        |<ul><li>- [x] (Through the dashboard only)</li></ul> |
|[Step Functions](#step-functions)       |All                        |<ul><li>- [ ] </li></ul>                             |
|[Generic](#generic)                     |All                        |<ul><li>- [ ] </li></ul>                             |
|[Gunicorn](#gunicorn)                   |`>=20.0.4`                 |<ul><li>- [x] </li></ul>                             |
|[Django](#django)                       |`>=1.11`                   |<ul><li>- [x] </li></ul>                             |
|[Flask](#flask)                         |`>=0.5`                    |<ul><li>- [x] </li></ul>                             |
|[Tornado](#tornado)                     |`>=4.0`                    |<ul><li>- [x] </li></ul>                             |
|[aiohttp](#aiohttp)                     |`>=3.0.0`                  |<ul><li>- [x] </li></ul>                             |
|[Celery](#celery)                       |`>=4.0.0`                  |<ul><li>- [x] </li></ul>                             |
|[Azure Functions](#azure-functions)     |`>=2.0.0`                  |<ul><li>- [ ] </li></ul>                             |
|[Chalice](#chalice)                     |`>=1.0.0`                  |<ul><li>- [ ] </li></ul>                             |
|[Zappa](#zappa)                         |`>=0.30.0`                 |<ul><li>- [ ] </li></ul>                             |


### AWS Lambda

Tracing Lambda functions can be done in three methods:
1. Auto-tracing through the Epsagon dashboard.
2. Using the [`serverless-plugin-epsagon`](https://github.com/epsagon/serverless-plugin-epsagon) if you're using The Serverless Framework.
3. Calling the SDK.

**Make sure to choose just one of the methods**

Calling the SDK is simple:

```python
import epsagon
epsagon.init(
    token='<epsagon-token>',
    app_name='<app-name-stage>',
    metadata_only=False,
)

# Wrap your entry point:
@epsagon.lambda_wrapper
def handle(event, context):
    # Your code is here
```

### Step Functions

Tracing Step Functions is similar to regular Lambda functions, but the wrapper changes from `lambda_wrapper` to `step_lambda_wrapper`:

```python
import epsagon
epsagon.init(
    token='<epsagon-token>',
    app_name='<app-name-stage>',
    metadata_only=False,
)

# Wrap your entry point:
@epsagon.step_lambda_wrapper
def handle(event, context):
    # Your code is here
```

### Django

Tracing Django application can be done in two methods:
1. [Auto-tracing](#auto-tracing) using the environment variable.
2. Calling the SDK.

Calling the SDK is simple, and should be done in your main `settings.py` file where the application is being initialized:
```python
import epsagon
epsagon.init(
    token='<epsagon-token>',
    app_name='<app-name-stage>',
    metadata_only=False,
)
```


### Flask

Tracing Flask application can be done in two methods:
1. [Auto-tracing](#auto-tracing) using the environment variable.
2. Calling the SDK.

Calling the SDK is simple, and should be done in your main `py` file where the application is being initialized:
```python
import epsagon
epsagon.init(
    token='<epsagon-token>',
    app_name='<app-name-stage>',
    metadata_only=False,
)
```

### Tornado

Tracing Tornado application can be done in two methods:
1. [Auto-tracing](#auto-tracing) using the environment variable.
2. Calling the SDK.

Calling the SDK is simple, and should be done in your main `py` file where the application is being initialized:
```python
import epsagon
epsagon.init(
    token='<epsagon-token>',
    app_name='<app-name-stage>',
    metadata_only=False,
)
```

### aiohttp

Tracing aiohttp application can be done in two methods:
1. [Auto-tracing](#auto-tracing) using the environment variable.
2. Calling the SDK.

Calling the SDK is simple, and should be done in your main `py` file where the application is being initialized:
```python
import epsagon
epsagon.init(
    token='<epsagon-token>',
    app_name='<app-name-stage>',
    metadata_only=False,
)
```

### Celery

Tracing Celery consumer can be done in two methods:
1. [Auto-tracing](#auto-tracing) using the environment variable.
2. Calling the SDK.

Calling the SDK is simple, and should be done in your main `py` file where the consumer is being initialized:
```python
import epsagon
epsagon.init(
    token='epsagon-token',
    app_name='app-name-stage',
    metadata_only=False,
)
```

### Gunicorn

Tracing Gunicorn application can be done in two methods:
1. [Auto-tracing](#auto-tracing) using the environment variable.
2. Calling the SDK.

Calling the SDK is simple, and should be done in your main `py` file where the application is being initialized:
```python
import epsagon
epsagon.init(
    token='<epsagon-token>',
    app_name='<app-name-stage>',
    metadata_only=False,
)
```

### Azure Functions

Tracing Azure Functions can be done in the following method:

```python
import azure.functions as func
import epsagon
epsagon.init(
    token='epsagon-token',
    app_name='app-name-stage',
    metadata_only=False,
)

@epsagon.azure_wrapper
def main(req):
    return func.HttpResponse('Success')
```

### Chalice

Tracing Chalice applications running on Lambda functions can be done by:
```python
from chalice import Chalice
import epsagon
epsagon.init(
    token='epsagon-token',
    app_name='app-name-stage',
    metadata_only=False
)
app = Chalice(app_name='hello-world')

# Your code is here

app = epsagon.chalice_wrapper(app)
```

### Zappa

Tracing web applications running on Lambda functions using Zappa can be done by:
```python
from zappa.handler import lambda_handler
import epsagon

epsagon.init(
    token='epsagon-token',
    app_name='app-name-stage',
    metadata_only=False
)

# Your code is here

epsagon_handler = epsagon.lambda_wrapper(lambda_handler)
```

And in your `zappa_settings.json` file include the following:

```json
{
  "lambda_handler": "module.path_to.epsagon_handler"
}
```

### Generic

For any tracing, you can simply use the generic Epsagon wrapper using the following example:

```python
import epsagon
epsagon.init(
    token='epsagon-token',
    app_name='app-name-stage',
    metadata_only=False,
)

# Wrap your entry point:
@epsagon.python_wrapper(name='my-resource')
def main(params):
    # Your code is here
```

## Integrations

Epsagon provides out-of-the-box instrumentation (tracing) for many popular frameworks and libraries.

|Library             |Supported Version          |
|--------------------|---------------------------|
|logging             |Fully supported            |
|urllib              |Fully supported            |
|urllib3             |Fully supported            |
|requests            |`>=2.0.0`                  |
|httplib2            |`>=0.9.2`                  |
|redis               |`>=2.10.0`                 |
|pymongo             |`>=3.0.0`                  |
|pynamodb            |`>=2.0.0`                  |
|PyMySQL             |`>=0.7.0`                  |
|MySQLdb             |`>=1.0.0`                  |
|psycopg2            |`>=2.2.0`                  |
|pg8000              |`>=1.9.0`                  |
|botocore (boto3)    |`>=1.4.0`                  |
|azure.cosmos        |`>=4.0.0`                  |
|celery              |`>=4.0.0`                  |
|grpc                |`>=0.3-10`                 |
|greengrasssdk       |`>=1.4.0`                 |
|SQLAlchemy                |`>=1.2.0`                 |



## Configuration

Advanced options can be configured as a parameter to the init() method or as environment variables.

|Parameter               |Environment Variable           |Type   |Default      |Description                                                                        |
|----------------------  |------------------------------ |-------|-------------|-----------------------------------------------------------------------------------|
|token                   |EPSAGON_TOKEN                  |String |-            |Epsagon account token                                                              |
|app_name                |EPSAGON_APP_NAME               |String |`Application`|Application name that will be set for traces                                       |
|metadata_only           |EPSAGON_METADATA               |Boolean|`True`       |Whether to send only the metadata (`True`) or also the payloads (`False`)          |
|use_ssl                 |EPSAGON_SSL                    |Boolean|`True`       |Whether to send the traces over HTTPS SSL or not                                   |
|collector_url           |EPSAGON_COLLECTOR_URL          |String |-            |The address of the trace collector to send trace to                                |
|keys_to_ignore          |EPSAGON_IGNORED_KEYS           |List   |-            |List of keys names to be removed from the trace                                    |
|keys_to_allow           |EPSAGON_ALLOWED_KEYS           |List   |-            |List of keys names to be included from the trace                                   |
|ignored_endpoints       |EPSAGON_ENDPOINTS_TO_IGNORE    |List   |-            |List of endpoints to ignore from tracing (for example `/healthcheck`               |
|url_patterns_to_ignore  |EPSAGON_URLS_TO_IGNORE         |List   |`[]`         |Array of URL patterns to ignore the calls                                          |
|debug                   |EPSAGON_DEBUG                  |Boolean|`False`      |Enable debug prints for troubleshooting                                            |
|disable_timeout_send    |EPSAGON_DISABLE_ON_TIMEOUT     |Boolean|`False`      |Disable timeout detection in Lambda functions                                      |
|split_on_send           |EPSAGON_SPLIT_ON_SEND          |Boolean|`False`      |Split the trace into multiple chunks to support large traces                       |
|propagate_lambda_id     |EPSAGON_PROPAGATE_LAMBDA_ID    |Boolean|`False`      |Insert Lambda request ID into the response payload                                 |
|logging_tracing_enabled |EPSAGON_LOGGING_TRACING_ENABLED|Boolean|`True`      |Add Epsagon Log Id to all `logging` messages                            |
|step_dict_output_path |EPSAGON_STEPS_OUTPUT_PATH|List|`None`      |Path in the result dict to append the Epsagon steps data  |
|-                       |EPSAGON_HTTP_ERR_CODE          |Integer|`500`        |The minimum number of an HTTP response status code to treat as an error            |
|-                       |EPSAGON_SEND_TIMEOUT_SEC       |Float  |`1.0`        |The timeout duration in seconds to send the traces to the trace collector          |
|-                       |EPSAGON_DISABLE_LOGGING_ERRORS |Boolean|`False`      |Disable the automatic capture of error messages into `logging`                     |
|-                       |DISABLE_EPSAGON                |Boolean|`False`      |A flag to completely disable Epsagon (can be used for tests or locally)            |
|-                       |DISABLE_EPSAGON_PATCH          |Boolean|`False`      |Disable the library patching (instrumentation)                                     |
|-                       |EPSAGON_LAMBDA_TIMEOUT_THRESHOLD_MS          |Integer|`200`      |The threshold in millieseconds to send the trace before a Lambda timeout occurs                                     |


## Getting Help

If you have any issue around using the library or the product, please don't hesitate to:

* Use the [documentation](https://docs.epsagon.com).
* Use the help widget inside the product.
* Open an issue in GitHub.


## Opening Issues

If you encounter a bug with the Epsagon library for Python, we want to hear about it.

When opening a new issue, please provide as much information about the environment:
* Library version, Python runtime version, dependencies, etc.
* Snippet of the usage.
* A reproducible example can really help.

The GitHub issues are intended for bug reports and feature requests.
For help and questions about Epsagon, use the help widget inside the product.

## License

Provided under the MIT license. See LICENSE for details.

Copyright 2020, Epsagon
