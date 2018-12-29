# Use an official Python runtime as a parent image
FROM python:3.6

# Install R to use rpy2 for access to R packages
RUN apt-get update && apt-get -y install r-base

# Adding backend directory to make absolute filepaths consistent in dev & prod
WORKDIR /app/backend

# Install R dependencies
COPY requirements.r /app/backend
RUN Rscript requirements.r

# Install Python dependencies
COPY requirements.txt /app/backend
RUN pip3 install --upgrade pip -r requirements.txt

# Add the rest of the code
COPY . /app/backend

# Make port 8888 available for Jupyter notebooks
EXPOSE 8888

# Make port 8000 available for the app
EXPOSE 8000

CMD python3 backend/manage.py runserver 0.0.0.0:8000
