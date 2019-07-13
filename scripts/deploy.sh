#!/bin/bash

set -euo pipefail

sudo chmod 600 ~/.ssh/deploy_rsa
sudo chmod 755 ~/.ssh
scp -i ~/.ssh/deploy_rsa docker-compose.prod.yml ${DEPLOY_USER}@${IP_ADDRESS}:/var/www/tipresias/docker-compose.yml

ssh -i ~/.ssh/deploy_rsa ${DEPLOY_USER}@${IP_ADDRESS} "docker pull cfranklin11/tipresias_app:latest \
  && docker-compose -f /var/www/tipresias/docker-compose.yml up -d --build"
