# Use an official node runtime as a parent image
FROM node:8@sha256:06adec3330444f71d8fd873600c20d6cec1aed6c26c714c881eebd03391814f2

# Install dependencies
COPY package.json yarn.lock /app/
WORKDIR /app/

RUN yarn

# Add rest of the client code
COPY . /app/

EXPOSE 3000

CMD yarn start
