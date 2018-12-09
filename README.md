# Tipresias
[![Build Status](https://travis-ci.com/cfranklin11/tipresias.svg?branch=master)](https://travis-ci.com/cfranklin11/tipresias)

>I Tipresias, old bot with dusty cores<br>
>Perceived the match, and foretold the score—<br>
>I too awaited the fanatics' roar.<br>

Child of [Footy Tipper](https://github.com/cfranklin11/footy-tipper), Tipresias, has, like Zeus before it, arisen to vanquish its father and claim its throne as the master of AFL footy tipping models.

## Running things

### Setup

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

### Run Python tests

- `docker-compose run --rm backend python3 -Wi manage.py test`
- Linting: `docker-compose run --rm backend pylint --disable=R <python modules you want to lint>`
    - Note: `-d=R` disables refactoring checks for quicker, less-opinionated linting. Remove that option if you want to include those checks.

### Deploy

- Via Travis CI (recommended):
    - In the Travis dashboard, navigate to the tipresias repository.
    - Under 'More Options', trigger a build on `master`.
    - This will build the image, run tests, and deploy to Heroku.
- Via heroku CLI (skips CI):
    - If your stack isn't set to container, run `heroku stack:set container`
    - `git push heroku master`

## Troubleshooting

- When working with some of the larger data sets (e.g. player stats comprise over 600,000 rows), your process might mysteriously die without completing. This is likely due to Docker running out of memory, because the default 2GB isn't enough. At least 4GB is the recommended limit, but you'll want more if you plan on having multiple processes running or multiple Jupyter notebooks open at the same time.
