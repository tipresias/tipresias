#!/bin/bash

set -euo pipefail

DROPLET_NAME=tipresias-app

echo Creating droplet...

DROPLET_IP=$(doctl compute droplet create \
  ${DROPLET_NAME} \
  --image docker-18-04 \
  --region sgp1 \
  --size s-1vcpu-1gb \
  --enable-monitoring \
  --enable-private-networking \
  --ssh-keys ${DIGITAL_OCEAN_SSH_KEYS} \
  --wait \
  --format PublicIPv4 \
  --no-header)

echo Droplet created!
echo Configuring droplet...

# Apparently it takes a bit for ssh to be ready to accept input
sleep 30

# We run setup script after droplet creation, because I can't figure out
# how to pass a file with an argument via --user-data/--user-data-file.
# We use 'ssh' instead of 'doctl compute ssh' to be able to bypass key checking.
ssh -oStrictHostKeyChecking=no root@${DROPLET_IP} \
  "bash -s" -- < ./scripts/digital_ocean_server_setup.sh ${DIGITAL_OCEAN_USER}

echo Droplet configured!
