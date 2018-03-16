#!/usr/bin/env python
from pip.req import parse_requirements
from pip.download import PipSession
from setuptools import setup, find_packages

install_reqs = parse_requirements('./requirements.txt', session=PipSession())
reqs = [str(ir.req) for ir in install_reqs]


setup(
    name='epsagon',
    version='0.1.1',
    description='Epsagon instrumentation for serverless Architecture Performance Monitoring',
    author='Epsagon',
    author_email='support@epsagon.com',
    url='https://github.com/epsagon/epsagon',
    packages=find_packages(exclude=('tests', 'examples')),
    install_requires=reqs,
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
