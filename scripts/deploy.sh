#!/bin/bash

set -euo pipefail

DOCKER_IMAGE=gcr.io/${PROJECT_ID}/${PROJECT_ID}-app

gcloud auth activate-service-account ${GC_SERVICE_ACCOUNT} \
  --key-file=${GOOGLE_APPLICATION_CREDENTIALS}
cat ${GOOGLE_APPLICATION_CREDENTIALS} | docker login -u _json_key --password-stdin gcr.io

docker pull ${DOCKER_IMAGE}
docker build --cache-from ${DOCKER_IMAGE} -t ${DOCKER_IMAGE} .
docker push ${DOCKER_IMAGE}

gcloud beta compute instances update-container ${PROJECT_ID}-app \
  --container-image ${DOCKER_IMAGE} \
  --zone australia-southeast1-b \
  --project ${PROJECT_ID}

./backend/scripts/wait-for-it.sh ${PRODUCTION_HOST}:${PORT:-8000} \
  -t 60 \
  -- ./scripts/migrate.sh

# Clean up old containers & images to avoid running out of disk space
./scripts/ssh.sh -- docker container ls --all --quiet --filter exited=1 | xargs docker container rm
./scripts/ssh.sh -- yes | docker image prune
