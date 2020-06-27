FROM scrapinghub/splash:3.5.0

# Splash expects to have the directory /etc/splash/filters, but for some reason
# it doesn't exist when running in Google Cloud Run, so we create it here.
# We can't just use mkdir, because Kaniko does weird stuff with permissions
# in Docker images, so we have to RUN a trivial command to load
# the base image's file system, then COPY an empty splash/filters directory
# into the image.
# There's probably a better way to do this, but it works, so whatever.
RUN true
COPY splash /etc/splash
