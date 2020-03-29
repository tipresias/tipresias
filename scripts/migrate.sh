#!/bin/bash

set -euo pipefail

./scripts/ssh.sh -- docker run \
  --rm \
  -e DJANGO_SETTINGS_MODULE=project.settings.production \
  -e SECRET_KEY=${SECRET_KEY} \
  -e DATABASE_URL=${DATABASE_URL} \
  gcr.io/${PROJECT_ID}/${PROJECT_ID}-app \
  python3 manage.py migrate
