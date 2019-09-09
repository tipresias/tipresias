DOCKER_COMPOSE_FILE="/var/www/tipresias/docker-compose.yml"
DOCKER_COMPOSE_RUN="docker-compose -f ${DOCKER_COMPOSE_FILE} run --rm app python3 backend/manage.py"

ssh ${PROD_USER}@${IP_ADDRESS} "${DOCKER_COMPOSE_RUN} tip && ${DOCKER_COMPOSE_RUN} send_email"
