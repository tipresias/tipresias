# Using frontend image for dev environment as base to avoid duplicating
# building the image, because Docker doesn't cache intermediate images
# in multistage builds
FROM cfranklin11/tipresias_frontend:latest AS frontend

WORKDIR /app

# Build static files
RUN yarn run build \
  && mkdir -p frontend/build/root \
  # Have to move all static files other than index.html to 'root'
  # for whitenoise middleware.
  # Moving all files except one is more complicated than I would have guessed
  # and varies by shell implementation, hence the convoluted command below.
  && find frontend/build -type f -maxdepth 1 -not -name index.html -exec mv {} frontend/build/root \; \
  && mv build/* frontend/build/

# Using Python base image instead of backend image, because we leave out
# many dev-only packages to reduce image size.
# Specifying the sha is to guarantee that CI will not try to rebuild from the
# source image (i.e. python:3.6), which apparently CIs are bad at avoiding on
# their own.
# Using slim-buster instead of alpine based on this GH comment:
# https://github.com/docker-library/python/issues/381#issuecomment-464258800
FROM python:3.8.1-slim-buster@sha256:dc9c4de1bb38720f70af28e8071f324052725ba122878fbac784be9b03f41590

# Install linux packages
RUN apt-get --no-install-recommends update \
  # g++ is a dependency of gcc, so must come before
  && apt-get -y --no-install-recommends install g++ gcc curl \
  && rm -rf /var/lib/apt/lists/*

# Set up backend dependencies & code
WORKDIR /app/backend
COPY ./backend/requirements.txt .
RUN pip3 install --upgrade pip -r requirements.txt
COPY ./backend .

COPY --from=frontend /app/frontend/build /app/frontend/build

# Collect static files
RUN mkdir staticfiles \
  && DJANGO_SETTINGS_MODULE=project.settings.production \
  # SECRET_KEY, API_TOKEN, and TIPPING_SERVICE_TOKEN are only included here
  # to avoid raising an error when generating static files. Be sure to add
  # real config/env variables in prod.
  SECRET_KEY=somethingsupersecret \
  API_TOKEN=notarealtoken \
  TIPPING_SERVICE_TOKEN=notrealeither \
  python3 manage.py collectstatic --noinput

# Gunicorn needs to be run from the backend directory to be able find the wsgi
# via python modules.
WORKDIR /app/backend

EXPOSE ${PORT:-80}

CMD gunicorn -b 0.0.0.0:80 -w 3 -t 1200 --access-logfile=- project.wsgi
