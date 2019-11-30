# Use an official node runtime as a parent image
FROM node:10.17@sha256:be69034700545030c110f67ae22e0584ddd59eeb2af81e4bd7f16f3ba5fa93a6

# Install dependencies
COPY package.json yarn.lock /app/
WORKDIR /app/

RUN yarn

# Add rest of the client code
COPY . /app/

EXPOSE 3000

CMD yarn start
