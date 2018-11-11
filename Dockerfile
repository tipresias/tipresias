# Use an official Python runtime as a parent image
FROM python:3.6

# Install R to use rpy2 for access to R packages
RUN apt-get update && apt-get -y install r-base

# Install curl, node, & yarn
RUN apt-get -y install curl
RUN curl -sL https://deb.nodesource.com/setup_8.x | bash \
  && apt-get install nodejs
RUN curl -o- -L https://yarnpkg.com/install.sh | bash

WORKDIR /app/

# Install R dependencies
COPY requirements.r /app/
RUN Rscript requirements.r

# Install Python dependencies
COPY requirements.txt /app/
RUN pip3 install --upgrade pip -r requirements.txt

# Install JS dependencies
WORKDIR /app/client/

COPY ./client/package.json ./client/yarn.lock /app/client/
RUN $HOME/.yarn/bin/yarn install

# Add the rest of the code
COPY . /app/

# Build static files
# RUN $HOME/.yarn/bin/yarn build

# Have to move all static files other than index.html to root/
# for whitenoise middleware
# WORKDIR /app/client/build

# RUN mkdir root
# RUN mv *.ico *.js *.json root

WORKDIR /app/

# Build static files
RUN mkdir staticfiles
RUN DJANGO_SETTINGS_MODULE=project.settings.production SECRET_KEY=somethingsupersecret python3 manage.py collectstatic --noinput

CMD python3 manage.py runserver 0.0.0.0:$PORT
