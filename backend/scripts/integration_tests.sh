#!/bin/bash

set -euo pipefail

docker-compose -f docker-compose.ci.yml stop
docker-compose -f docker-compose.ci.yml up -d
./backend/scripts/wait-for-it.sh localhost:3000 -t 30 -- echo "Server ready"

docker-compose -f docker-compose.ci.yml run --rm backend coverage run manage.py test --no-input

docker-compose -f docker-compose.ci.yml stop
