# !/bin/bash

set -euo pipefail

npx fauna add-endpoint http://faunadb:8443/ --alias localhost --key secret
npx fauna delete-database ${DATABASE_NAME} --endpoint localhost
npx fauna create-database ${DATABASE_NAME} --endpoint localhost
npx fauna create-key ${DATABASE_NAME} --endpoint localhost
