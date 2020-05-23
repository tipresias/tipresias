#! /bin/bash

set -euo pipefail

RUN_TIP="
  docker exec ${PROJECT_ID}_app python3 manage.py tip \
    && docker exec ${PROJECT_ID}_app python3 manage.py send_email
"

./scripts/ssh.sh ${RUN_TIP}
