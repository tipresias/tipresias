# Tipresias

[![Build Status](https://travis-ci.com/tipresias/tipresias.svg?branch=master)](https://travis-ci.com/tipresias/tipresias)

> I Tipresias, old bot with dusty cores<br>
> Perceived the match, and foretold the score—<br>
> I too awaited the fanatics' roar.<br>

Child of [Footy Tipper](https://github.com/cfranklin11/footy-tipper), Tipresias, has, like Zeus before it, arisen to vanquish its father and claim its throne as the master of AFL footy tipping models.

## Running things

### Setup

- Create the `node_modules` volume: `docker volume create --name=node_modules`
- To build and run the app: `docker-compose up --build`
- Migrate the DB: `docker-compose run --rm backend python3 manage.py migrate`
- Seed the DB: `docker-compose run --rm backend python3 manage.py seed_db`

### Run the app

- `docker-compose up`
- Navigate to `localhost:3000`.

### Run Jupyter notebook in Docker

- If it's not already running, run Jupyter with `docker-compose up notebook`.
- The terminal will display something like the following message:

```
notebook_1  | [I 03:01:38.909 NotebookApp] The Jupyter Notebook is running at:
notebook_1  | [I 03:01:38.909 NotebookApp] http://(ea7b71b85805 or 127.0.0.1):8888/?token=dhf7674ururrtuuf8968lhhjdrfjghicty57t69t85e6dhfj
notebook_1  | [I 03:01:38.909 NotebookApp] Use Control-C to stop this server and shut down all kernels (twice to skip confirmation).
```

- Copy the URL given and paste it into your browser.
- Alternatively, copy just the token from the terminal, navigate your browser to `http://localhost:8888`, and paste the token into the given field.

### Testing

#### Run Python tests

- `docker-compose run --rm backend python3 -Wi manage.py test`
- Linting: `docker-compose run --rm backend pylint --disable=R <python modules you want to lint>`
  - Note: `-d=R` disables refactoring checks for quicker, less-opinionated linting. Remove that option if you want to include those checks.

#### Run Javascript tests

- `docker-compose run --rm frontend yarn run test:unit`
- Linting: `docker-compose run --rm frontend yarn run eslint src`
  - Note: The ESLint rule `"import/no-unresolved"` is disabled, because code editors can't find the `node_modules` inside the docker container, and it made everything red. Also, basic testing should catch erroneous imports anyway.
- Flow: `docker-compose run --rm frontend yarn run flow`

#### Run R tests

- `docker-compose run --rm afl_data Rscript -e "devtools::test()"`

### Deploy

- Via Travis CI (recommended):
  - In the Travis dashboard, navigate to the tipresias repository.
  - Under 'More Options', trigger a build on `master`.
  - This will build the image, run tests, and deploy to DigitalOcean.

- Deploy `afl_data` to Google Cloud:
  - `gcloud builds submit --config cloudbuild.yaml ./afl_data`
  - `gcloud beta run deploy $SERVICE_NAME --image gcr.io/$PROJECT_ID/afl_data`

## Pro-Tips

- Both `backend` and `frontend` are encapsulated, with their dependencies, in their respective containers, so if you want to take advantage of in-editor linting, autofixing, etc., open your editor from the service directory, not the project directory. Be sure to run terminal commands from the project root, though.

## Troubleshooting

- When working with some of the larger data sets (e.g. player stats comprise over 600,000 rows), your process might mysteriously die without completing. This is likely due to Docker running out of memory, because the default 2GB isn't enough. At least 4GB is the recommended limit, but you'll want more if you plan on having multiple processes running or multiple Jupyter notebooks open at the same time.
