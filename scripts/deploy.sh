#!/bin/bash

set -euo pipefail

DOCKER_IMAGE="gcr.io/${PROJECT_ID}/tipresias:latest"

gcloud auth configure-docker
docker pull $DOCKER_IMAGE
docker build --cache-from $DOCKER_IMAGE -t $DOCKER_IMAGE .
docker push $DOCKER_IMAGE
