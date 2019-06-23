echo "$DOCKER_PASSWORD" | docker login -u cfranklin11 --password-stdin
docker push cfranklin11/tipresias_server:master
docker push cfranklin11/tipresias_client:master
docker push cfranklin11/tipresias_afl_data:latest
docker push cfranklin11/tipresias_browser_test:latest

docker pull cfranklin11/tipresias_app:latest
docker build --cache-from cfranklin11/tipresias_app:latest -t cfranklin11/tipresias_app:latest .
docker push cfranklin11/tipresias_app:latest

sudo chmod 600 ~/.ssh/deploy_rsa
sudo chmod 755 ~/.ssh
scp -i ~/.ssh/deploy_rsa docker-compose.prod.yml ${DEPLOY_USER}@${IP_ADDRESS}:~/tipresias/docker-compose.yml

ssh -i ~/.ssh/deploy_rsa ${DEPLOY_USER}@${IP_ADDRESS} "docker pull cfranklin11/tipresias_app:latest \
  && docker-compose -f ./tipresias/docker-compose.yml up -d --build"
