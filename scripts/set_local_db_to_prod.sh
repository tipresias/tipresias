#!/bin/bash

set -euo pipefail

if [ -z "$1" ]
then
  DB_FILE=prod_dump_`date +%Y-%m-%d"_"%H_%M_%S`.sql

  # Requires objectCreator/objectViewer roles for the SQL service account
  gcloud sql export sql ${PROJECT_ID}-db gs://${PROJECT_ID}_db_backups/${DB_FILE} --database ${DATABASE_NAME}
  gsutil cp gs://${PROJECT_ID}_db_backups/${DB_FILE} $PWD/db/backups
else
  DB_FILE=$1
fi

docker-compose rm -s -v db
docker-compose up -d db

# Not ideal, but wait-for-it was listening for the port to be ready, but that
# wasn't enough time for the DB to be ready to accept commands,
# so we're sleeping instead
sleep 4

# Google Cloud SQL dumps include the following roles. PostGres raises errors
# if they don't exist in the local DB.
docker exec -t -u postgres tipresias_db_1 psql \
  --command="CREATE ROLE cloudsqladmin" \
  --dbname=${DATABASE_NAME}
docker exec -t -u postgres tipresias_db_1 psql \
  --command="CREATE ROLE cloudsqlsuperuser" \
  --dbname=${DATABASE_NAME}
cat $PWD/db/backups/${DB_FILE} \
  | docker exec -i tipresias_db_1 psql -U postgres -d ${DATABASE_NAME}
