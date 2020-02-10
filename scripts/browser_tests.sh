#!/bin/bash

set -euo pipefail

docker-compose -f docker-compose.ci.yml stop
docker-compose -f docker-compose.ci.yml up -d

./browser_test/wait-for-it.sh localhost:3000 -t 30 -- \
  docker-compose -f docker-compose.ci.yml run --rm backend \
  python3 server/tests/fixtures/seed_db.py

docker-compose -f docker-compose.ci.yml run --rm browser_test npx cypress run

docker-compose -f docker-compose.ci.yml stop
