# Use an official Python runtime as a parent image
FROM python:3.6

# Install R to use rpy2 for access to R packages
RUN apt-get update && apt-get -y install r-base

RUN apt-get update && apt-get -y install curl
RUN curl -sL https://deb.nodesource.com/setup_8.x | bash \
  && apt-get install nodejs
RUN curl -o- -L https://yarnpkg.com/install.sh | bash

# Install dependencies
COPY requirements.txt /app/
WORKDIR /app/

# Install dependencies
COPY requirements.r /app/
RUN Rscript requirements.r

COPY requirements.txt /app/
RUN pip install --upgrade pip --trusted-host pypi.python.org -r requirements.txt

# Add the rest of the code
COPY . /app/
WORKDIR /app/client/

RUN $HOME/.yarn/bin/yarn install
RUN yarn build

WORKDIR /app/

# Make port 8000 available for the app
EXPOSE 8000

# CMD craft serve
CMD python3 manage.py runserver
