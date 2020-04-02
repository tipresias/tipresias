#!/bin/bash

set -euo pipefail

gcloud compute ssh \
  --project ${PROJECT_ID} \
  --zone australia-southeast1-b \
  --command "$*" \
  ${PROJECT_ID}-app
