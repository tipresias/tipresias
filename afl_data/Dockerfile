FROM r-base

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