#!/bin/bash

set -euo pipefail

DOCKER_IMAGE=cfranklin11/tipresias_app:latest

docker pull ${DOCKER_IMAGE}
docker build --cache-from ${DOCKER_IMAGE} -t ${DOCKER_IMAGE} .
docker push ${DOCKER_IMAGE}

gcloud auth activate-service-account ${GC_SERVICE_ACCOUNT} --key-file=${GOOGLE_APPLICATION_CREDENTIALS}
gcloud beta compute instances update-container ${PROJECT_ID}-app --container-image ${DOCKER_IMAGE} --zone australia-southeast1-b --project ${PROJECT_ID}
