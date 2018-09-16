# Use an official Python runtime as a parent image
FROM node:8

# Add package.json for js dependencies
COPY package.json yarn.lock /app/
WORKDIR /app/

# Install any needed packages specified in package.json
RUN yarn

# Add the resources directory with frontent files
COPY ./storage/ /app/storage/

EXPOSE 3000

# In production, we just need to build the compiled assets
CMD yarn run build