# Use an official Python runtime as a parent image
# Specifying the sha is to guarantee that CI will not try to rebuild from the
# source image (i.e. python:3.6), which apparently CIs are bad at avoiding on
# their own
FROM python:3.6@sha256:00110125bd9c23f200cfd2cfa82e68b8ab2006e1358f7a048e005794aa51568f

WORKDIR /app

# Install Python dependencies
COPY requirements.txt /app
RUN pip3 install --upgrade pip -r requirements.txt

# Add the rest of the code
COPY . /app

# Make port 8888 available for Jupyter notebooks
EXPOSE 8888

# Make port 8008 available for the app
EXPOSE 8008
