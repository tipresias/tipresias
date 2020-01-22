#! /bin/bash

set -euo pipefail

./scripts/ssh.sh python3 backend/manage.py tip \
  && python3 backend/manage.py send_email
