#! /bin/bash

set -euo pipefail

./scripts/ssh.sh docker run \
  --rm \
  -e DJANGO_SETTINGS_MODULE=project.settings.production \
  -e SECRET_KEY=${SECRET_KEY} \
  -e DATABASE_URL=${DATABASE_URL} \
  -e PYTHON_ENV=production \
  -e GCPF_TOKEN=${GCPF_TOKEN} \
  -e DATA_SCIENCE_SERVICE=${DATA_SCIENCE_SERVICE} \
  -e FOOTY_TIPS_USERNAME=${FOOTY_TIPS_USERNAME} \
  -e FOOTY_TIPS_PASSWORD=${FOOTY_TIPS_PASSWORD} \
  gcr.io/${PROJECT_ID}/${PROJECT_ID}-app \
  python3 manage.py tip

# I can't get the method for running multiple commands in docker
# (bin/bash -c "<commands>") to work in Google Compute Engine,
# so I'll just run them separately.
./scripts/ssh.sh docker run \
  --rm \
  -e DJANGO_SETTINGS_MODULE=project.settings.production \
  -e SECRET_KEY=${SECRET_KEY} \
  -e DATABASE_URL=${DATABASE_URL} \
  -e PYTHON_ENV=production \
  -e GCPF_TOKEN=${GCPF_TOKEN} \
  -e DATA_SCIENCE_SERVICE=${DATA_SCIENCE_SERVICE} \
  -e FOOTY_TIPS_USERNAME=${FOOTY_TIPS_USERNAME} \
  -e FOOTY_TIPS_PASSWORD=${FOOTY_TIPS_PASSWORD} \
  gcr.io/${PROJECT_ID}/${PROJECT_ID}-app \
  python3 manage.py send_email
