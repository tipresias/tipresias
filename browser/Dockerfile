FROM cypress/browsers:node10.2.1-chrome74@sha256:21d6232541c3d99409edcdd2b581784a93cb0ffe43bb845f07f62c8d693a9b1c
WORKDIR /app

COPY package.json package-lock.json ./

# by setting CI environment variable we switch the Cypress install messages
# to small "started / finished" and avoid 1000s of lines of progress messages
# https://github.com/cypress-io/cypress/issues/1243
ENV CI=1
RUN npm install
# verify that Cypress has been installed correctly.
# running this command separately from "cypress run" will also cache its result
# to avoid verifying again when running the tests
RUN npx cypress verify

COPY wait-for-it.sh .
