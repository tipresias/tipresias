# Use an official node runtime as a parent image
FROM node:8

# Install dependencies
COPY package.json yarn.lock /app/
WORKDIR /app/

RUN yarn

# Add rest of the client code
COPY . /app/

EXPOSE 3000

CMD yarn start
