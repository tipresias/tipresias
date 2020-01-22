#!/bin/bash

if [ -z "$*" ]
then
  COMMAND_ARG=""
else
  COMMAND_ARG="-- $*"
fi

gcloud compute ssh \
  --project ${PROJECT_ID} \
  --zone australia-southeast1-b \
  ${PROJECT_ID}-app \
  ${COMMAND_ARG}
