#!/bin/bash

set -euo pipefail

APP_DIR=/var/www/${PROJECT_ID}

COMMAND="cd ${APP_DIR}"

if [ "$*" ]
then
  COMMAND="${COMMAND}; $*"
else
  COMMAND="${COMMAND}; bash"
fi

ssh -t ${DIGITAL_OCEAN_USER}@${PRODUCTION_HOST} "${COMMAND}"
