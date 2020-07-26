#!/bin/bash

set -euo pipefail

CI=${CI:-"false"}
DOCKER_COMPOSE_FILE="${1:-docker-compose.yml}"

docker-compose -f ${DOCKER_COMPOSE_FILE} up -d

./scripts/wait-for-it.sh localhost:3000 -t 30 -- \
  docker-compose -f ${DOCKER_COMPOSE_FILE} run --rm frontend \
    yarn run apollo client:download-schema --config=src/apollo.config.js

docker-compose -f ${DOCKER_COMPOSE_FILE} run --rm frontend \
  yarn run apollo client:codegen graphql-types \
    --target=flow \
    --includes=src/graphql/index.js \
    --tagName=gql \
    --localSchemaFile=schema.json

if [[ $CI = "true" ]]
then
  git diff --color --exit-code frontend/schema.json
fi
