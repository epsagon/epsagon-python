#!/usr/bin/env bash
cd acceptance/lambda-handlers

build_num=$1

function run_acceptance_test() {
    runtime=$1
    echo "deploying of ${runtime} [build: ${build_num}]"
    serverless deploy --runtime ${runtime} --buildNumber ${build_num} || {  echo "deployment of ${runtime} [build: ${build_num}] failed" ; exit 1; }
    serverless invoke -f sanity --runtime ${runtime} --buildNumber ${build_num}  || {  echo "test ${runtime} [build: ${build_num}] failed" ; serverless remove --runtime ${runtime}  --buildNumber ${build_num} ; exit 1; }
    serverless invoke -f sanity --runtime ${runtime} --buildNumber ${build_num} -p bad_events.json || {  echo "test ${runtime} [build: ${build_num}] with bad event arguments failed" ; serverless remove --runtime ${runtime}  --buildNumber ${build_num} ; exit 1; }
    serverless invoke -f labels --runtime ${runtime} --buildNumber ${build_num} || {  echo "test ${runtime} [build: ${build_num}] labels failed" ; serverless remove --runtime ${runtime}  --buildNumber ${build_num} ; exit 1; }
    serverless remove --runtime ${runtime} --buildNumber ${build_num}
}

run_acceptance_test py36
run_acceptance_test py27

cd -
exit 0
