#!/bin/bash

DB_FILE=dump_`date +%d-%m-%Y"_"%H_%M_%S`.sql

ssh ${PROD_USER}@${IP_ADDRESS} "docker exec -t -u postgres tipresias_db_1 pg_dumpall -c > ~/${DB_FILE}"
scp ${PROD_USER}@${IP_ADDRESS}:~/${DB_FILE} $PWD
ssh ${PROD_USER}@${IP_ADDRESS} "rm ~/${DB_FILE}"

docker-compose rm -s -v db
docker-compose up -d db
# Not ideal, but wait-for-it was listening for the port to be ready, but that
# wasn't enough time for the DB to be ready to accept commands,
# so we're sleeping instead
sleep 3
cat ${DB_FILE} | docker exec -i tipresias_db_1 psql -Upostgres
