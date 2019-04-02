# Use an official Python runtime as a parent image
# Specifying the sha is to guarantee that CI will not try to rebuild from the
# source image (i.e. python:3.6), which apparently CIs are bad at avoiding on
# their own
FROM python:3.6@sha256:be8258268093afd16846564e3963af3059fd341e16677d7cd0bc157f0d7fcdfa

# Install R to use rpy2 for access to R packages
RUN apt-get update && apt-get -y install r-base

# Install curl, node, & yarn
RUN apt-get -y install curl
RUN curl -sL https://deb.nodesource.com/setup_8.x | bash \
  && apt-get install nodejs
RUN curl -o- -L https://yarnpkg.com/install.sh | bash

WORKDIR /app/backend

# Install R dependencies
COPY ./backend/requirements.r /app/backend/
RUN Rscript requirements.r

# Install Python dependencies
COPY ./backend/requirements.txt /app/backend/
RUN pip3 install --upgrade pip -r requirements.txt

# Install JS dependencies
WORKDIR /app/frontend

COPY ./frontend/package.json ./frontend/yarn.lock /app/frontend/
RUN $HOME/.yarn/bin/yarn install

# Add the rest of the code, ignoring files not needed in prod
ENV STR=$'notebooks'
RUN echo "$STR" >> .dockerignore
COPY . /app/

# Build static files
RUN $HOME/.yarn/bin/yarn build

# Have to move all static files other than index.html to root/
# for whitenoise middleware
WORKDIR /app/frontend/build

RUN mkdir root
RUN mv *.ico *.js *.json root

WORKDIR /app/backend

# Build static files
RUN mkdir staticfiles

WORKDIR /app

# SECRET_KEY is only included here to avoid raising an error when generating static files.
# Be sure to add a real SECRET_KEY config variable in Heroku.
RUN DJANGO_SETTINGS_MODULE=project.settings.production \
  SECRET_KEY=somethingsupersecret \
  python3 backend/manage.py collectstatic --noinput

CMD python3 backend/manage.py runserver 0.0.0.0:$PORT
