# Specifying the sha is to guarantee that CI will not try to rebuild from the
# source image (i.e. node:13.5), which apparently CIs are bad at avoiding on
# their own.
# Using buster-slim instead of alpine, because there's an open issue
# about flow not working on alpine, and the response is *shrug*
FROM node:13.7.0-buster-slim@sha256:9c638051657f3514fc2a449d6e8859ee0b2e12fde8cd1d057f0bc7bf28db84e4

WORKDIR /app

# Install dependencies
COPY package.json yarn.lock ./
RUN yarn

# Add rest of the client code
COPY . .

EXPOSE 3000

CMD yarn start
