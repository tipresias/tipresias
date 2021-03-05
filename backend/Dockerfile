# Specifying the sha is to guarantee that CI will not try to rebuild from the
# source image (i.e. python:3.6), which apparently CIs are bad at avoiding on
# their own.
# Using slim-buster instead of alpine based on this GH comment:
# https://github.com/docker-library/python/issues/381#issuecomment-464258800
FROM python:3.9.2-slim-buster@sha256:70b693f32768b122a6a5247b0c5d4394da69f5dc3baace93a34860bff00d8ecd

RUN apt-get --no-install-recommends update \
  # g++ is a dependency of gcc, so must come before
  && apt-get -y --no-install-recommends install g++ gcc \
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

CMD gunicorn -b 0.0.0.0:80000 -w 3 -t 600 --access-logfile=- project.wsgi
