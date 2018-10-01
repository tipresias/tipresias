# Use an official Python runtime as a parent image
FROM node:8

# Add client files
COPY ./client/ /app/
WORKDIR /app/

# Install any needed packages specified in package.json
RUN yarn

EXPOSE 3000

# Since backend serves the assets in production, it depends on build/ in development as well,
# so we need to make sure build/index.html exists in all environments
RUN yarn run build
