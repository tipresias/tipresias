#!/bin/bash

set -euo pipefail

APP_DIR=/var/www/${PROJECT_ID}
DOCKER_IMAGE=cfranklin11/${PROJECT_ID}_app:latest
PORT=80
TRAVIS=${TRAVIS:-""}

if [ "${TRAVIS}" ]
then
  sudo chmod 600 ~/.ssh/deploy_rsa
  sudo chmod 755 ~/.ssh
fi

# docker pull ${DOCKER_IMAGE}
# docker build --cache-from ${DOCKER_IMAGE} -t ${DOCKER_IMAGE} .
# docker push ${DOCKER_IMAGE}

scp -i ~/.ssh/deploy_rsa -oStrictHostKeyChecking=no \
  docker-compose.prod.yml \
  ${DIGITAL_OCEAN_USER}@${PRODUCTION_HOST}:${APP_DIR}/docker-compose.yml

RUN_APP="
  cd ${APP_DIR} \
    && docker pull ${DOCKER_IMAGE} \
    && docker-compose stop \
    && docker-compose up -d
"

# We use 'ssh' instead of 'doctl compute ssh' to be able to bypass key checking.
ssh -i ~/.ssh/deploy_rsa -oStrictHostKeyChecking=no \
  ${DIGITAL_OCEAN_USER}@${PRODUCTION_HOST} \
  ${RUN_APP}

if [ $? != 0 ]
then
  exit $?
fi

./backend/scripts/wait-for-it.sh ${PRODUCTION_HOST}:${PORT} \
  -t 60 \
  -- ./scripts/post_deploy.sh

exit $?
