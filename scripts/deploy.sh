#!/bin/bash

set -euo pipefail

DOCKER_COMPOSE_FILE=/var/www/tipresias/docker-compose.yml

sudo chmod 600 ~/.ssh/deploy_rsa
sudo chmod 755 ~/.ssh
scp -i ~/.ssh/deploy_rsa docker-compose.prod.yml ${DEPLOY_USER}@${IP_ADDRESS}:${DOCKER_COMPOSE_FILE}

ssh -i ~/.ssh/deploy_rsa ${DEPLOY_USER}@${IP_ADDRESS} "docker pull cfranklin11/tipresias_app:latest \
  && docker-compose -f ${DOCKER_COMPOSE_FILE} up -d --build \
  && docker-compose -f ${DOCKER_COMPOSE_FILE} run --rm app python3 backend/manage.py migrate"
