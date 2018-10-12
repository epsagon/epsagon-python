#!/usr/bin/env python
import re
import os
from setuptools import setup, find_packages

try:
    # For pip >= 10.
    from pip._internal.req import parse_requirements
    from pip._internal.download import PipSession
except ImportError:
    # For pip <= 9.0.3.
    from pip.req import parse_requirements
    from pip.download import PipSession

install_reqs = parse_requirements('./requirements.txt', session=PipSession())
reqs = [str(ir.req) for ir in install_reqs]

# Get version
with open(os.path.join('epsagon', 'constants.py'), 'rt') as consts_file:
    version = re.search(r'__version__ = \'(.*?)\'', consts_file.read()).group(1)

setup(
    name='epsagon',
    version=version,
    description='Epsagon Instrumentation for Python',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Epsagon',
    author_email='support@epsagon.com',
    url='https://github.com/epsagon/epsagon-python',
    packages=find_packages(exclude=('tests', 'examples')),
    install_requires=reqs,
    license='MIT',
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
    keywords=[
        'serverless',
        'epsagon',
        'tracing',
        'distributed-tracing',
        'lambda',
        'aws-lambda',
        'debugging',
        'monitoring'
    ],
    classifiers=(
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.6',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
    )
)
