#!/bin/bash

set -euo pipefail

DOCKER_COMPOSE_FILE="${1:-docker-compose.yml}"

docker-compose -f $DOCKER_COMPOSE_FILE run --rm backend \
  python3 manage.py graphql_schema --out server/new.graphql

docker-compose -f $DOCKER_COMPOSE_FILE run --rm graphql_inspector

mv backend/server/new.graphql backend/server/schema.graphql
