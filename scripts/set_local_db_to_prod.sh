#!/bin/bash

set -euo pipefail

FILE_ARG=${1:-""}

if [ -z ${FILE_ARG} ]
then
  PROJECT_DIR=${PWD}
  DATABASE_FILE=prod_dump_`date +%Y-%m-%d"_"%H_%M_%S`.sql

  ssh ${DATABASE_USER}@${DATABASE_HOST} "bash -s" -- \
    < ./scripts/dump_prod_db.sh ${DATABASE_NAME} ${DATABASE_FILE} ${DATABASE_PASSWORD}
  scp ${DATABASE_USER}@${DATABASE_HOST}:${DATABASE_FILE} ${PWD}/db/backups/${DATABASE_FILE}
  ssh ${DATABASE_USER}@${DATABASE_HOST} rm ${DATABASE_FILE}
else
  DATABASE_FILE=${FILE_ARG}
fi

docker-compose rm -s -v db
docker-compose up -d db

# Not ideal, but wait-for-it was listening for the port to be ready, but that
# wasn't enough time for the DB to be ready to accept commands,
# so we're sleeping instead
sleep 7

cat $PWD/db/backups/${DATABASE_FILE} \
  | docker exec -i tipresias_db_1 psql -U postgres -d ${DATABASE_NAME}
