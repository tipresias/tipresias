# Use an official Python runtime as a parent image
FROM python:3

# Install R to use rpy2 for access to R packages
RUN apt-get update && apt-get -y install r-base

# Install dependencies
COPY requirements.txt /app/
WORKDIR /app/

RUN pip3 install --trusted-host pypi.python.org -r requirements.txt

COPY requirements.r /app/
RUN Rscript requirements.r

# Add the rest of the code
COPY . /app/

# Make port 8888 available for Jupyter notebooks
EXPOSE 8888

# Make port 8000 available for the app
EXPOSE 8000

# CMD craft serve
CMD python3 manage.py runserver
