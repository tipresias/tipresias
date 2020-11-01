# Specifying the sha is to guarantee that CI will not try to rebuild from the
# source image (i.e. python:3.6), which apparently CIs are bad at avoiding on
# their own.
# Using slim-buster instead of alpine based on this GH comment:
# https://github.com/docker-library/python/issues/381#issuecomment-464258800
FROM python:3.9.0-slim-buster@sha256:de73afabeb56845daee86de96e86960d906e975fe7210b6675bf40002eebcc09

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
COPY requirements.txt .
RUN pip3 install --upgrade pip -r requirements.txt

# Add the rest of the code
COPY . .
