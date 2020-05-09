#!/bin/bash


set -euo pipefail

APP_DIR=/var/www/${PROJECT_ID}
DOCKER_IMAGE=cfranklin11/${PROJECT_ID}_app:latest
PORT=80

sudo chmod 600 ~/.ssh/deploy_rsa
sudo chmod 755 ~/.ssh

docker pull ${DOCKER_IMAGE}
docker build --cache-from ${DOCKER_IMAGE} -t ${DOCKER_IMAGE} .
docker push ${DOCKER_IMAGE}

RUN_APP="
  cd ${APP_DIR} \
    && docker pull ${DOCKER_IMAGE} \
    && docker stop ${PROJECT_ID}_app \
    && docker container rm ${PROJECT_ID}_app \
    && docker run \
      -d \
      --env-file .env \
      -p ${PORT}:${PORT} \
      -e DJANGO_SETTINGS_MODULE=project.settings.production \
      -e NODE_ENV=production \
      --name ${PROJECT_ID}_app \
      ${DOCKER_IMAGE}
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
