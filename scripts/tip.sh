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
  /bin/bash -c "python3 manage.py tip; python3 manage.py send_email"
