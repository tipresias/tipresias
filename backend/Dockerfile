# Use an official Python runtime as a parent image
# Specifying the sha is to guarantee that CI will not try to rebuild from the
# source image (i.e. python:3.6), which apparently CIs are bad at avoiding on
# their own
FROM python:3.6@sha256:00110125bd9c23f200cfd2cfa82e68b8ab2006e1358f7a048e005794aa51568f

# Adding backend directory to make absolute filepaths consistent in dev & prod
WORKDIR /app/backend

# Install firefox & geckodriver for use by selenium
RUN apt-get update \
  && apt-get -y install firefox-esr \
  && wget https://github.com/mozilla/geckodriver/releases/download/v0.24.0/geckodriver-v0.24.0-linux64.tar.gz \
  && tar -xvzf geckodriver* \
  && chmod +x geckodriver \
  && mv geckodriver /usr/local/bin/

# Install Python dependencies
COPY requirements.txt /app/backend
RUN pip3 install --upgrade pip -r requirements.txt

# Add the rest of the code
COPY . /app/backend

# Make port 8888 available for Jupyter notebooks
EXPOSE 8888

# Make port 8000 available for the app
EXPOSE 8000

CMD python3 manage.py runserver 0.0.0.0:8000
