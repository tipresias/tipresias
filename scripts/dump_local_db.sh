#!/bin/bash

DB_FILE=local_dump_`date +%Y-%m-%d"_"%H_%M_%S`.sql

# Including a bunch of extra options for compatibility with Google Cloud SQL
docker exec -t -u postgres tipresias_db_1 pg_dump -U postgres --format=plain --no-owner --no-acl tipresias \
  | sed -E 's/(DROP|CREATE|COMMENT ON) EXTENSION/-- \1 EXTENSION/g' > "${DB_FILE}"
