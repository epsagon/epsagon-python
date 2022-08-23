#!/usr/bin/env bash
if [ -z $AWS_ACCESS_KEY_ID ] || [ -z $AWS_SECRET_ACCESS_KEY ]; then
    echo "AWS credentials must be set in order to run acceptance tests"
    exit 1
elif [ $TRAVIS_PYTHON_VERSION != "2.7" ]; then
    npm install && export PATH=$(pwd)/node_modules/.bin:$PATH
    ./acceptance/run.sh $TRAVIS_BUILD_NUMBER $TRAVIS_PYTHON_VERSION
elif [ $TRAVIS_PYTHON_VERSION != "3.6" ]; then
    npm install && export PATH=$(pwd)/node_modules/.bin:$PATH
    ./acceptance/run.sh $TRAVIS_BUILD_NUMBER $TRAVIS_PYTHON_VERSION
fi
