echo "$DOCKER_PASSWORD" | docker login -u cfranklin11 --password-stdin
docker pull cfranklin11/tipresias_app:latest
docker build --cache-from cfranklin11/tipresias_app:latest -t cfranklin11/tipresias_app:latest .
docker push cfranklin11/tipresias_app:latest
ssh -i deploy_rsa ${DEPLOY_USER}@${IP_ADDRESS} "docker pull cfranklin11/tipresias_app:latest && docker-compose restart"