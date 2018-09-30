# Use an official Python runtime as a parent image
FROM node:8

# Add client files
COPY ./client/ /app/
WORKDIR /app/

# Install any needed packages specified in package.json
RUN yarn

EXPOSE 3000

# The server uses build/index.html as a template, so we have to build
# to make sure the server doesn't raise a template error
RUN yarn run build
