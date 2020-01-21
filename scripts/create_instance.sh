gcloud beta compute instances create-with-container tipresias-app \
  --container-env DATA_SCIENCE_SERVICE=${DATA_SCIENCE_SERVICE},DATABASE_URL=${DATABASE_URL},DJANGO_SETTINGS_MODULE=project.settings.production,EMAIL_RECIPIENT=${EMAIL_RECIPIENT},FOOTY_TIPS_USERNAME=${FOOTY_TIPS_USERNAME},FOOTY_TIPS_PASSWORD=${FOOTY_TIPS_PASSWORD},GCPF_TOKEN=${GCPF_TOKEN},NODE_ENV=production,PRODUCTION_HOST=${PRODUCTION_HOST},PROJECT_ID=${PROJECT_ID},PYTHON_ENV=production,SENDGRID_API_KEY=${SENDGRID_API_KEY},SECRET_KEY=${SECRET_KEY}\
  --container-image ${DOCKER_IMAGE} \
  --machine-type g1-small \
  --network-tier STANDARD \
  --zone australia-southeast1-b \
  --tags http-server,https-server \
  --metadata-from-file startup-script=./scripts/startup_script.sh
