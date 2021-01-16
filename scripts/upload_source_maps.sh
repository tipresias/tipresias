# !/bin/bash

set -euo pipefail

echo "Uploading source maps for version $COMMIT_HASH!"

# We upload a source map for each resulting JavaScript
# file; the path depends on your build config
for path in $(find frontend/build/static/js -name "main.*.js"); do
  # URL of the JavaScript file on the web server
  url=http://tipresias.net/${path}

  # a path to a corresponding source map file
  source_map="@$path.map"

  echo "\\nUploading source map for $url"

  curl --silent --show-error https://api.rollbar.com/api/1/sourcemap \
    -F access_token=$ROLLBAR_TOKEN \
    -F version=$COMMIT_HASH \
    -F minified_url=$url \
    -F source_map=$source_map \
    > /dev/null
done
