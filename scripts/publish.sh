#!/usr/bin/env bash
echo "releasing new version..." &&
./scripts/semantic_release.sh &&
sleep 1 &&
echo "publishing layer..." &&
./scripts/publish_layer.sh &&
echo "deployment successful"
