# Use an official Python runtime as a parent image
# Specifying the sha is to guarantee that CI will not try to rebuild from the
# source image (i.e. python:3.6), which apparently CIs are bad at avoiding on
# their own.
# Using slim-buster instead of alpine based on this GH comment:
# https://github.com/docker-library/python/issues/381#issuecomment-464258800
# TODO: Might be able to switch to alpine when we remove pandas and/or numpy
# as dependencies
FROM python:3.8.0-slim-buster@sha256:8e243f41e500238f78f7a29a81656114d3fe603d5c34079a462d090f71c4b225

# Install firefox & geckodriver for use by selenium
RUN apt-get --no-install-recommends update \
  # g++ is a dependency of gcc, so must come before
  && apt-get -y --no-install-recommends install g++ gcc wget firefox-esr \
  && wget https://github.com/mozilla/geckodriver/releases/download/v0.24.0/geckodriver-v0.24.0-linux64.tar.gz \
  && tar -xvzf geckodriver* \
  && chmod +x geckodriver \
  && mv geckodriver /usr/local/bin/ \
  && rm -rf /var/lib/apt/lists/*

# Adding backend directory to make absolute filepaths consistent in dev & prod
WORKDIR /app/backend

# Install Python dependencies
COPY requirements.txt .
RUN pip3 install --upgrade pip -r requirements.txt

# Add the rest of the code
COPY . .

# Make port 8000 available for the app
EXPOSE 8000

CMD python3 manage.py runserver 0.0.0.0:8000
