# A Bit awkward, but preferable to the alternative:
# we use a different Dockerfile for CI, because Google Cloud can't deploy
# when we specify the image with '@sha256', but without it, Travis rebuilds
# the image from scratch every time.
# The parent image is r-base:3.6.0
FROM r-base@sha256:302874713b0a8b9d11b5811f9b57b1e4d96c4f03c258a34c5978f14783b2814f

RUN apt-get update && apt-get -y install \
  libcurl4-openssl-dev \
  libxml2 \
  libxml2-dev \
  libssl-dev

WORKDIR /app/afl_data

COPY init.R ./
RUN Rscript init.R

COPY . /app/afl_data

EXPOSE 8080

CMD Rscript app.R
