#!/bin/bash

#### SETUP ####
DOCKER_COMPOSE_FILE="${1:-docker-compose.yml}"

DEFAULT_DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE}
DEFAULT_NODE_ENV=${NODE_ENV}

export DJANGO_SETTINGS_MODULE=project.settings.test
export NODE_ENV=test

docker-compose -f ${DOCKER_COMPOSE_FILE} up -d

#### SEED TEST DB ####
./scripts/wait-for-it.sh localhost:8000 -t 30 -- \
  docker-compose -f ${DOCKER_COMPOSE_FILE} run --rm \
    backend python3 server/tests/fixtures/seed_db.py

# We manually manage exit codes rather than using pipefail, because we want
# to be sure to stop docker-compose before exiting.
EXIT_CODE=$?

if [ ${EXIT_CODE} != 0 ]
then
  # Need to stop before exiting to reset to non-test env vars
  docker-compose -f ${DOCKER_COMPOSE_FILE} stop

  export DJANGO_SETTINGS_MODULE=${DEFAULT_DJANGO_SETTINGS_MODULE}
  export NODE_ENV=${DEFAULT_NODE_ENV}

  docker-compose up -d

  exit ${EXIT_CODE}
fi

#### RUN TESTS ####

# There's probably a better way to do this, but we change the default DB name
# to test_$DATABASE_NAME, which the app will then use as the default DB
# for the browser tests. This follows Django's naming convention for test DBs.
DEFAULT_DATABASE_NAME=${DATABASE_NAME}
export DATABASE_NAME="test_${DEFAULT_DATABASE_NAME}"

# Restarting backend for the new env var to be used
docker-compose -f ${DOCKER_COMPOSE_FILE} stop backend
docker-compose -f ${DOCKER_COMPOSE_FILE} up -d backend

./scripts/wait-for-it.sh localhost:8000 -t 30 -- \
  docker-compose -f ${DOCKER_COMPOSE_FILE} run --rm \
    browser_test npx cypress run

EXIT_CODE=$?

#### CLEANUP ####
# Need to stop before exiting to reset to non-test env vars
docker-compose run --rm tipresias_db_1 psql \
  -U postgres \
  -d ${DATABASE_NAME} \
  --command "DROP DATABASE ${DATABASE_NAME}"
docker-compose -f ${DOCKER_COMPOSE_FILE} stop

export DJANGO_SETTINGS_MODULE=${DEFAULT_DJANGO_SETTINGS_MODULE}
export NODE_ENV=${DEFAULT_NODE_ENV}
export DATABASE_NAME=${DEFAULT_DATABASE_NAME}

docker-compose up -d

if [ ${EXIT_CODE} -eq 0 ]
then
  exit ${EXIT_CODE}
fi

#### UPLOAD SCREENSHOTS ####
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
