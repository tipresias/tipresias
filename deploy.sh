echo "$DOCKER_PASSWORD" | docker login -u cfranklin11 --password-stdin
docker pull cfranklin11/tipresias_app:latest
docker build --cache-from cfranklin11/tipresias_app:latest -t cfranklin11/tipresias_app:latest .
docker push cfranklin11/tipresias_app:latest
scp -i ~/.ssh/deploy_rsa docker-compose.prod.yml ${DEPLOY_USER}@${IP_ADDRESS}:~/tipresias/docker-compose.yml
ssh -i ~/.ssh/deploy_rsa ${DEPLOY_USER}@${IP_ADDRESS} "docker pull cfranklin11/tipresias_app:latest && docker-compose -f ./tipresias/docker-compose.yml up -d --build"
