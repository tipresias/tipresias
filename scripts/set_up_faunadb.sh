#!/bin/bash
set -euo pipefail

FAUNA_SHELL_VERSION=$(fauna --version)
echo "Fauna Shell: ${FAUNA_SHELL_VERSION}"

DIRENV_VERSION=$(direnv --version)
echo "Direnv: ${DIRENV_VERSION}"

docker-compose up -d faunadb
# wait-for-it doesn't give the DB time to be ready to receive commands, so we sleep for a bit
sleep 2

[ -z "$(fauna list-endpoints | grep localhost)" ] \
  && fauna add-endpoint http://localhost:8443/ --alias localhost --key secret

[ -z "$(fauna list-databases --endpoint=localhost | grep tipresias)" ] \
  && fauna create-database tipresias --endpoint=localhost

touch .env

if [ -z "$(cat .env | grep FAUNADB_KEY)" ]
then
  # create-key command includes the line "  secret: <API token string>"
  FAUNADB_KEY="$(fauna create-key tipresias --endpoint=localhost | grep secret: | cut -d " " -f 4)"
  echo "FAUNADB_KEY=${FAUNADB_KEY}" >> .env

  direnv reload
fi
