#!/bin/bash

set -euo pipefail

DOCKER_COMPOSE_FILE="${1:-docker-compose.yml}"

docker-compose -f ${DOCKER_COMPOSE_FILE} up -d
./scripts/wait-for-it.sh localhost:3000 -t 30 -- echo "Server ready"

# App backend tests
echo "Running backend integration tests..."
docker-compose -f ${DOCKER_COMPOSE_FILE} run --rm backend \
  coverage run manage.py test --no-input
docker-compose -f ${DOCKER_COMPOSE_FILE} run --rm backend coverage xml

# Tipping service tests
echo "Running tipping service integration tests..."
docker-compose -f ${DOCKER_COMPOSE_FILE} run --rm tipping \
  coverage run -m pytest src/tests
docker-compose -f ${DOCKER_COMPOSE_FILE} run --rm tipping coverage xml
