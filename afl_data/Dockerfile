FROM r-base@sha256:452d2ca0fd9a76314dfaba4681d0b2189d3966b64fabbb41cc071c805ff1f430

RUN apt-get update && apt-get -y install \
  libcurl4-openssl-dev \
  libxml2 \
  libxml2-dev \
  libssl-dev

WORKDIR /app/afl_data

COPY init.R DESCRIPTION packrat.lock ./
RUN Rscript init.R

COPY . /app/afl_data

EXPOSE 8001

CMD Rscript app.R
