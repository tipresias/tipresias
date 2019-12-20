# Use an official node runtime as a parent image
FROM node:13.5.0@sha256:c2b3be4bc9c765c3bd062885ef0284ddc5b0660e0a3a489335018069f152c768

# Install dependencies
COPY package.json yarn.lock /app/
WORKDIR /app/

RUN yarn

# Add rest of the client code
COPY . /app/

EXPOSE 3000

CMD yarn start
