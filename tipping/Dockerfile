# Specifying the sha is to guarantee that CI will not try to rebuild from the
# source image (i.e. python:3.6), which apparently CIs are bad at avoiding on
# their own.
# Using slim-buster instead of alpine based on this GH comment:
# https://github.com/docker-library/python/issues/381#issuecomment-464258800
FROM python:3.8.6-slim-buster@sha256:3a751ba465936180c83904df83436e835b9a919a6331062ae764deefbd3f3b47

RUN apt-get --no-install-recommends update \
  # g++ is a dependency of gcc, so must come before
  && apt-get -y --no-install-recommends install g++ gcc curl \
  && curl -sL https://deb.nodesource.com/setup_12.x | bash - \
  && apt-get -y --no-install-recommends install nodejs \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install NPM dependencies
COPY package.json package-lock.json ./
RUN npm install

# Install Python dependencies
COPY requirements.txt requirements.prod.txt ./
COPY ./sqlalchemy-fauna/ ./sqlalchemy-fauna/
RUN pip3 install --upgrade pip -r requirements.txt

# Add the rest of the code
COPY . .
