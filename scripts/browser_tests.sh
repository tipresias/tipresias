#!/bin/bash

docker-compose -f docker-compose.ci.yml stop
docker-compose -f docker-compose.ci.yml up -d

./browser_test/wait-for-it.sh localhost:3000 -t 30 -- \
  docker-compose -f docker-compose.ci.yml run --rm backend \
  python3 server/tests/fixtures/seed_db.py

docker-compose -f docker-compose.ci.yml run --rm browser_test npx cypress run

EXIT_CODE=$?

docker-compose -f docker-compose.ci.yml stop

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
