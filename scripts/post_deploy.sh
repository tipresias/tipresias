#!/bin/bash

set -euo pipefail

# This script runs the following commands:
MIGRATE_DB="
  docker run \
    --rm \
    -e DJANGO_SETTINGS_MODULE=project.settings.production \
    -e SECRET_KEY=${SECRET_KEY} \
    -e DATABASE_URL=${DATABASE_URL} \
    gcr.io/${PROJECT_ID}/${PROJECT_ID}-app \
    python3 manage.py migrate
"

# Re remove exited containers & prune images in order to avoid running out of disk space
REMOVE_STALE_CONTAINERS="
  STALE_CONTAINERS=\$(docker container ls --all --quiet --filter exited=1)
  [ -z \"\${STALE_CONTAINERS}\" ] && echo \"No stale containers to remove\" \
    || \${STALE_CONTAINERS} | xargs docker container rm
"
PRUNE_IMAGES="yes | docker image prune"

# We pass a blank ssh config file to avoid locale errors that result
# from ssh trying to transmit LC_* env vars.
touch ssh_config

gcloud compute ssh \
  --project=${PROJECT_ID} \
  --zone=australia-southeast1-b \
  --ssh-flag="-F ./ssh_config" \
  --command="
    ${MIGRATE_DB}
    ${REMOVE_STALE_CONTAINERS}
    ${PRUNE_IMAGES}
  " \
  ${PROJECT_ID}-app
