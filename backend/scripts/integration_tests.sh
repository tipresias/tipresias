#!/bin/bash

set -euo pipefail

DOCKER_COMPOSE_FILE="${1:-docker-compose.yml}"

docker-compose -f ${DOCKER_COMPOSE_FILE} stop
docker-compose -f ${DOCKER_COMPOSE_FILE} up -d
./backend/scripts/wait-for-it.sh localhost:3000 -t 30 -- echo "Server ready"

docker-compose -f ${DOCKER_COMPOSE_FILE} run --rm backend \
  coverage run manage.py test --no-input
docker-compose -f ${DOCKER_COMPOSE_FILE} run --rm backend coverage xml

docker-compose -f ${DOCKER_COMPOSE_FILE} stop
