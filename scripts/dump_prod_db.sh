#!/bin/bash
set -euo pipefail

DATABASE_NAME=$1
DATABASE_FILE=$2
PASSWORD=$3

echo ${PASSWORD} \
  | sudo -S -u postgres pg_dump \
    --format=plain \
    --no-owner \
    --no-acl \
    ${DATABASE_NAME} \
  | sed -E "s/(DROP|CREATE|COMMENT ON) EXTENSION/-- \1 EXTENSION/g" > ${DATABASE_FILE}
