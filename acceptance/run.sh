#!/usr/bin/env bash
cd acceptance/lambda-handlers

build_num=$1
result=0
function run_acceptance_test() {
    runtime=$1
    echo "deploying of ${runtime} [build: ${build_num}]"
    serverless deploy --runtime ${runtime} --buildNumber ${build_num} || {  echo "deployment of ${runtime} [build: ${build_num}] failed" ; result=1; }
    pytest ../acceptance.py || {  echo "tests ${runtime} [build: ${build_num}] failed" ; result=1; }
    serverless remove --runtime ${runtime} --buildNumber ${build_num}
}

run_acceptance_test python3.6
#run_acceptance_test python3.7
run_acceptance_test python2.7

cd -
exit ${result}
