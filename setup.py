#!/usr/bin/env python
from pip.req import parse_requirements
from pip.download import PipSession
from setuptools import setup
import epsagon.constants

install_reqs = parse_requirements('./requirements.txt', session=PipSession())
reqs = [str(ir.req) for ir in install_reqs]


setup(
    name='epsagon',
    version=epsagon.constants.__version__,
    description='Epsagon instrumentation for serverless Architecture Performance Monitoring',
    author='Epsagon',
    author_email='support@epsagon.com',
    url='https://github.com/epsagon/epsagon',
    packages=['epsagon'],
    install_requires=reqs,
    extras_require={
        'dev': [
            'flake8'
        ]
    },
    license="Apache License 2.0",
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
    keywords=[ 'distributedtracing', 'epsagon', 'tracing', 'serverless', 'microservices', 'lambda' ],
    classifiers=(
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
    )
)
