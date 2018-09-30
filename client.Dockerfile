# Use an official Python runtime as a parent image
FROM node:8

# Add client files
COPY ./client/ /app/
WORKDIR /app/

# Install any needed packages specified in package.json
RUN yarn

EXPOSE 3000

# In production, we just need to build the compiled assets
CMD yarn run build