# Use an official Python runtime as a parent image
FROM python:3.6

# Install R to use rpy2 for access to R packages
RUN apt-get update && apt-get -y install r-base
RUN R -e "install.packages('devtools', repos='https://mirror.aarnet.edu.au/pub/CRAN/')"

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

# Add the rest of the code
COPY . /app/

# Install JS dependencies
WORKDIR /app/client/

RUN $HOME/.yarn/bin/yarn install
RUN $HOME/.yarn/bin/yarn build

WORKDIR /app/

# Make port 8000 available for the app
EXPOSE 8000

# CMD craft serve
CMD python3 manage.py runserver 0.0.0.0:$PORT
