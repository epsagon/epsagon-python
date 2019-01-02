#!/bin/sh
declare -a regions=("ap-northeast-1" "ap-northeast-2" "ap-south-1" "ap-southeast-1" "ap-southeast-2" "ca-central-1" "eu-central-1" "eu-west-1" "eu-west-2" "eu-west-3" "sa-east-1" "us-east-1" "us-east-2" "us-west-1" "us-west-2")
mkdir python
pip install epsagon -t python/
zip -r epsagon-python-layer.zip python -x ".*" -x "__MACOSX" -x "*.pyc" -x "*__pycache__*"
rm -Rf python/

for region in "${regions[@]}"
do
    echo ${region}
    aws s3 cp epsagon-python-layer.zip s3://epsagon-layers-${region}/
    LAYER_VERSION=$(aws lambda publish-layer-version --layer-name epsagon-python-layer --description "Epsagon Python layer that includes pre-installed packages to get up and running with monitoring and distributed tracing" --content S3Bucket=epsagon-layers-${region},S3Key=epsagon-python-layer.zip --compatible-runtimes python3.7 python3.6 python2.7 --license-info MIT --region ${region} | jq '.Version')
    aws lambda add-layer-version-permission --layer-name epsagon-python-layer --version-number ${LAYER_VERSION} --statement-id sid1 --action lambda:GetLayerVersion --principal \* --region ${region}
done

rm epsagon-python-layer.zip