# Specifying the sha is to guarantee that CI will not try to rebuild from the
# source image (i.e. node:13.5), which apparently CIs are bad at avoiding on
# their own.
# Using buster-slim instead of alpine, because there's an open issue
# about flow not working on alpine, and the response is *shrug*
FROM node:14.0.0-buster-slim@sha256:ff304c945ee51b3a8e1465f835a2ca3e3d335c3de56c74af35461af877e08a30

WORKDIR /app

# Install dependencies
COPY package.json yarn.lock ./
RUN yarn

# Add rest of the client code
COPY . .

EXPOSE 3000

CMD yarn start
