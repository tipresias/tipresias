#!/bin/bash

set -euo pipefail

docker-compose run --rm frontend yarn run apollo client:download-schema \
  --config=src/apollo.config.js
docker-compose run --rm frontend yarn run apollo client:codegen \
  graphql-types \
  --target=flow \
  --includes=src/graphql/index.js \
  --tagName=gql \
  --localSchemaFile=schema.json
