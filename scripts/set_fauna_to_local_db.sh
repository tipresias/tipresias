#!/bin/bash

set -euo pipefail

PROJECT_DIR=${PWD}
DATABASE_FILE=local_dump_`date +%Y-%m-%d"_"%H_%M_%S`.json
DATABASE_FILEPATH=${PROJECT_DIR}/db/backups/${DATABASE_FILE}
TIPPING_FILEPATH=${PROJECT_DIR}/tipping/${DATABASE_FILE}

docker-compose run --rm backend python3 manage.py dumpdata \
  --output ${DATABASE_FILE} \
  --indent 2 \
  --exclude auth \
  --exclude contenttypes

# Save file in backups just in case
mv ${PROJECT_DIR}/backend/${DATABASE_FILE} ${DATABASE_FILEPATH}
cp ${DATABASE_FILEPATH} ${TIPPING_FILEPATH}

docker-compose run --rm tipping python3 scripts/reset_fauna_data.py ${DATABASE_FILE}

rm ${TIPPING_FILEPATH}
