#!/bin/bash

#### SETUP ####
DOCKER_COMPOSE_FILE="${1:-docker-compose.yml}"
export DJANGO_SETTINGS_MODULE=project.settings.test
export NODE_ENV=test

docker-compose -f ${DOCKER_COMPOSE_FILE} stop
docker-compose -f ${DOCKER_COMPOSE_FILE} up -d

#### SEED TEST DB ####
./browser_test/wait-for-it.sh localhost:8000 -t 30 -- \
  docker-compose -f ${DOCKER_COMPOSE_FILE} run --rm \
    backend python3 server/tests/fixtures/seed_db.py

# We manually manage exit codes rather than using pipefail, because we want
# to be sure to stop docker-compose before exiting.
EXIT_CODE=$?

if [ ${EXIT_CODE} != 0 ]
then
  docker-compose -f ${DOCKER_COMPOSE_FILE} stop
  exit ${EXIT_CODE}
fi

#### RUN TESTS ####

# There's probably a better way to do this, but we change the default DB name
# to test_$DATABASE_NAME, which the app will then use as the default DB
# for the browser tests.
export DATABASE_NAME="test_${DATABASE_NAME}"

# Restarting backend for the new env var to be used
docker-compose -f ${DOCKER_COMPOSE_FILE} stop backend
docker-compose -f ${DOCKER_COMPOSE_FILE} up -d backend

./browser_test/wait-for-it.sh localhost:8000 -t 30 -- \
  docker-compose -f ${DOCKER_COMPOSE_FILE} run --rm \
    browser_test npx cypress run

EXIT_CODE=$?

#### CLEANUP ####
docker-compose -f ${DOCKER_COMPOSE_FILE} stop

if [ ${EXIT_CODE} -eq 0 ]
then
  exit ${EXIT_CODE}
fi

LOCAL_DIR=${PWD}/browser_test/cypress/screenshots
BUCKET_DIR=`date +%Y-%m-%d"_"%H_%M_%S`

# Only upload screenshots to a bucket if in CI, because we'll have access
# to the image files on local
if [ -d "${LOCAL_DIR}" ] && [ "${CI}" = "true" ]
then
  echo "Uploading screenshots to Google Cloud Storage."

  gcloud auth activate-service-account ${GC_SERVICE_ACCOUNT} \
    --key-file=${GOOGLE_APPLICATION_CREDENTIALS}

  gsutil cp -r ${LOCAL_DIR} gs://${PROJECT_ID}_travis_artifacts/${BUCKET_DIR}
fi

exit ${EXIT_CODE}
