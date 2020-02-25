#!/bin/bash

docker-compose -f docker-compose.ci.yml stop
docker-compose -f docker-compose.ci.yml up -d

# We don't technically need the frontend server to be ready, but it's a safe way
# to make sure the database is ready to import data.
./browser_test/wait-for-it.sh localhost:3000 -t 30 -- \
  docker-compose -f docker-compose.ci.yml run \
    --rm backend \
    python3 server/tests/fixtures/seed_db.py

# There's probably a better way to do this, but we change the default DB name
# to test_$DATABASE_NAME, which the app will then use as the default DB
# for the browser tests.
ORIGINAL_DB_NAME=${DATABASE_NAME}
export DATABASE_NAME="test_${DATABASE_NAME}"

# Restarting backend for the new env var to be used
docker-compose -f docker-compose.ci.yml stop backend
docker-compose -f docker-compose.ci.yml up -d backend

./browser_test/wait-for-it.sh localhost:3000 -t 30 -- \
  docker-compose -f docker-compose.ci.yml run \
    --rm browser_test npx cypress run

EXIT_CODE=$?

docker-compose -f docker-compose.ci.yml stop

# Resetting the env var to the original just in case
export DATABASE_NAME=${ORIGINAL_DB_NAME}

if [ ${EXIT_CODE} -eq 0 ]
then
  exit ${EXIT_CODE}
fi

LOCAL_DIR=${PWD}/browser_test/cypress/screenshots
BUCKET_DIR=`date +%Y-%m-%d"_"%H_%M_%S`

if [ -d "${LOCAL_DIR}" ]
then
  gcloud auth activate-service-account ${GC_SERVICE_ACCOUNT} \
    --key-file=${GOOGLE_APPLICATION_CREDENTIALS}

  gsutil cp -r ${LOCAL_DIR} gs://${PROJECT_ID}_travis_artifacts/${BUCKET_DIR}
fi

exit ${EXIT_CODE}
