# Specifying the sha is to guarantee that CI will not try to rebuild from the
# source image (i.e. node:13.5), which apparently CIs are bad at avoiding on
# their own.
# Using buster-slim instead of alpine, because there's an open issue
# about flow not working on alpine, and the response is *shrug*
FROM node:13.5.0-buster-slim@sha256:cc8594c222457a525e04b0af1e2a8ffa6a9dcb9e9d3e6ce4e03a881d449ce8d4 AS frontend

WORKDIR /app/frontend

# Set up frontend code & dependencies
COPY ./frontend/package.json ./frontend/yarn.lock ./
RUN yarn
COPY ./frontend .

# Build static files
RUN yarn run build
WORKDIR /app/frontend/build
# Have to move all static files other than index.html to root/
# for whitenoise middleware
RUN mkdir root && mv *.ico *.js *.json root

# Use an official Python runtime as a parent image
# Specifying the sha is to guarantee that CI will not try to rebuild from the
# source image (i.e. python:3.6), which apparently CIs are bad at avoiding on
# their own.
# Using slim-buster instead of alpine based on this GH comment:
# https://github.com/docker-library/python/issues/381#issuecomment-464258800
# TODO: Might be able to switch to alpine when we remove pandas and/or numpy
# as dependencies
FROM python:3.8.0-slim-buster@sha256:8e243f41e500238f78f7a29a81656114d3fe603d5c34079a462d090f71c4b225

# Install linux packages
RUN apt-get --no-install-recommends update \
  # g++ is a dependency of gcc, so must come before
  && apt-get -y --no-install-recommends install g++ gcc \
  && rm -rf /var/lib/apt/lists/*

# Set up backend dependencies & code
WORKDIR /app/backend
COPY ./backend/requirements.txt .
RUN pip3 install --upgrade pip -r requirements.txt
COPY ./backend .

# Build static files
WORKDIR /app
COPY --from=frontend /app/frontend/build /app/frontend/build
RUN mkdir /app/backend/staticfiles

RUN DJANGO_SETTINGS_MODULE=project.settings.production \
  # SECRET_KEY is only included here to avoid raising an error when generating static files.
  # Be sure to add a real SECRET_KEY config/env variable in prod.
  SECRET_KEY=somethingsupersecret \
  python3 backend/manage.py collectstatic --noinput

CMD python3 backend/manage.py runserver 0.0.0.0:$PORT
