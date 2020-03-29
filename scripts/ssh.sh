#!/bin/bash

set -euo pipefail

# Note: Can't figure out how to run multiple commands on GC's version of ssh,
# because all the usual solutions don't seem to work.
gcloud compute ssh \
  --project ${PROJECT_ID} \
  --zone australia-southeast1-b \
  ${PROJECT_ID}-app \
  $*
