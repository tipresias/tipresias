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

# Clean up old containers & images to avoid running out of disk space.
# We pass a blank ssh config file to avoid locale errors that result
# from ssh trying to transmit LC_* env vars.
touch ssh_config

gcloud compute ssh \
  --project ${PROJECT_ID} \
  --zone australia-southeast1-b \
  --ssh-flag="-F ./ssh_config" \
  ${PROJECT_ID}-app \
  -- docker container ls --all --quiet --filter exited=1 | xargs docker container rm

gcloud compute ssh \
  --project ${PROJECT_ID} \
  --zone australia-southeast1-b \
  --ssh-flag="-F ./ssh_config" \
  ${PROJECT_ID}-app \
  -- yes | docker image prune
