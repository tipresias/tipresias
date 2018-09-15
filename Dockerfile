# Use an official Python runtime as a parent image
FROM python:3

# Install R to use rpy2 for access to R packages
RUN apt-get update && apt-get -y install r-base

# Add our code
ADD ./ /app
WORKDIR /app

# Install any needed packages specified in requirements.txt
RUN pip3 install --trusted-host pypi.python.org -r requirements.txt

# Install fitzRoy R package
RUN Rscript requirements.r

# Make port 8888 available to the world outside this container
EXPOSE 8888
