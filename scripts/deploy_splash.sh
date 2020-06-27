#!/bin/bash

set -euo pipefail

gcloud builds submit splash \
  --config splash/cloudbuild.yaml \
  --ignore-file .dockerignore

gcloud beta run deploy splash \
  --image gcr.io/${PROJECT_ID}/splash \
  --memory 2048Mi \
  --region us-central1 \
  --platform managed \
  --port 8050 \
  --timeout 900 \
  --max-instances 5
