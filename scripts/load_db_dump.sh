#!/bin/bash


set -euo pipefail

DB_FILE_PATH=${1}

docker-compose rm -s -v db
docker-compose up -d db

# Not ideal, but wait-for-it was listening for the port to be ready,
# but that wasn't enough time for the DB to be ready to accept commands,
# so we're sleeping instead
sleep 10

docker-compose exec db \
  cockroach sql --execute "CREATE DATABASE IF NOT EXISTS ${DB_NAME};" --insecure
docker-compose exec db \
  cockroach sql --file /cockroach/${DB_FILE_PATH} --insecure
