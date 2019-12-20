# Use an official Python runtime as a parent image
# Specifying the sha is to guarantee that CI will not try to rebuild from the
# source image (i.e. python:3.6), which apparently CIs are bad at avoiding on
# their own
FROM python:3.8.0@sha256:76aace0349933165c34ae8f99b32d269103bc14818c1914b104c34521b92f288

# Install curl, node, & yarn
RUN apt-get -y install curl \
  && curl -sL https://deb.nodesource.com/setup_8.x | bash \
  && apt-get install nodejs \
  && curl -o- -L https://yarnpkg.com/install.sh | bash

WORKDIR /app/backend

# Install firefox & geckodriver for use by selenium
RUN apt-get update \
  && apt-get -y install firefox-esr \
  && wget https://github.com/mozilla/geckodriver/releases/download/v0.24.0/geckodriver-v0.24.0-linux64.tar.gz \
  && tar -xvzf geckodriver* \
  && chmod +x geckodriver \
  && mv geckodriver /usr/local/bin/

# Install Python dependencies
COPY ./backend/requirements.txt /app/backend/
RUN pip3 install --upgrade pip -r requirements.txt

# Install JS dependencies
WORKDIR /app/frontend

COPY ./frontend/package.json ./frontend/yarn.lock /app/frontend/
RUN $HOME/.yarn/bin/yarn install

# Add frontend code
COPY ./frontend /app/frontend/

# Build static files
RUN $HOME/.yarn/bin/yarn build

# Have to move all static files other than index.html to root/
# for whitenoise middleware
WORKDIR /app/frontend/build

RUN mkdir root && mv *.ico *.js *.json root

# Add backend code
COPY ./backend /app/backend/

# Build static files
RUN mkdir /app/backend/staticfiles

WORKDIR /app

# SECRET_KEY is only included here to avoid raising an error when generating static files.
# Be sure to add a real SECRET_KEY config/env variable in prod.
RUN DJANGO_SETTINGS_MODULE=project.settings.production \
  SECRET_KEY=somethingsupersecret \
  python3 backend/manage.py collectstatic --noinput

CMD python3 backend/manage.py runserver 0.0.0.0:$PORT
