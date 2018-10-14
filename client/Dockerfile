# Use an official node runtime as a parent image
FROM node:8

# Install dependencies
COPY package.json yarn.lock /app/
WORKDIR /app/

RUN yarn

# Add rest of the client code
COPY . /app/

EXPOSE 3000

# Since backend serves the assets in production, it depends on build/ in development as well,
# so we need to make sure build/index.html exists in all environments
CMD yarn run build
