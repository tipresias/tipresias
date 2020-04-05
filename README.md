# Tipresias

[![Build Status](https://travis-ci.com/tipresias/tipresias.svg?branch=master)](https://travis-ci.com/tipresias/tipresias)
<a href="https://codeclimate.com/github/tipresias/tipresias/maintainability"><img src="https://api.codeclimate.com/v1/badges/b6a40f7f72b307763b88/maintainability" /></a>
<a href="https://codeclimate.com/github/tipresias/tipresias/test_coverage"><img src="https://api.codeclimate.com/v1/badges/b6a40f7f72b307763b88/test_coverage" /></a>

> I Tipresias, old bot with dusty cores<br>
> Perceived the match, and foretold the score—<br>
> I too awaited the fanatics' roar.<br>

Child of [Footy Tipper](https://github.com/cfranklin11/footy-tipper), Tipresias, has, like Zeus before it, arisen to vanquish its father and claim its throne as the master of AFL footy tipping models.

## Running things

### Setup

#### Install dependencies

- Install [`direnv`](https://direnv.net/)
  - Loads env vars from `.env`, which is convenient
- `brew cask install google-cloud-sdk` (on Mac)
  - For interacting with production resources (e.g. ssh into the prod server, dumping prod DB data)
- Install Docker

#### Set up development environment and the app itself

- To manage environment variables:
  - Add `eval "$(direnv hook bash)"` to the bottom of `~/.bashrc`
  - Run `direnv allow .` inside the project directory
- To set up the app:
  - Create the `node_modules` volume: `docker volume create --name=node_modules`
  - To build and run the app: `docker-compose up --build`
  - Migrate the DB: `docker-compose run --rm backend python3 manage.py migrate`
- To use Google Cloud SDK:
  - `gcloud auth login` (redirects you to log into your Google account in the browser)
  - `gcloud config set project ${PROJECT_ID}`

#### Generate data for `data_science`

The following are only required for using functionality from `tip` or `seed_db` Django commands:
  - Generate data set files: `docker-compose run --rm data_science ./scripts/generate_data_sets.sh`
  - Generate trained model files: `docker-compose run --rm data_science python3 scripts/save_default_models.py`

#### Seed data

**Recommended:** `./scripts/set_local_db_to_prod.sh`
  - Downloads the production database and loads it on local

Seed the DB with raw data: `docker-compose run --rm backend python3 manage.py seed_db`
  - This takes a very long time, so it's recommended that you reset the DB as described below if possible

### Run the app

- `docker-compose up`
- Navigate to `localhost:3000`.

#### Useful commands

- To `ssh` into the server, run `./scripts/ssh.sh`.
- To run the tipping command, run `./scripts/tip.sh`.

### A note on architecture

- `tipresias` depends on two micro-services: [`bird-signs`](https://github.com/tipresias/bird-signs) for raw data and [`augury`](https://github.com/tipresias/augury) for machine-learning functionality (i.e. generating model predictions). In the dev environment, this is managed via docker-compose, which uses the images of these services; in production, the app calls relevant Google Cloud functions. If one of these services isn't working on local, try pulling the latest image, as something might have changed.

### Testing

#### Run Python tests

- `docker-compose run --rm backend python3 -Wi manage.py test`
  - Note: Pass CI=true as an env var to skip some of the longer end-to-end tests.
- Linting: `docker-compose run --rm backend pylint --disable=R <python modules you want to lint>`
  - Note: `-d=R` disables refactoring checks for quicker, less-opinionated linting. Remove that option if you want to include those checks.
- Type checking: `docker-compsoe run mypy <python modules you want to check>`

#### Run Javascript tests

- `docker-compose run --rm frontend yarn run test:unit`
- Linting: `docker-compose run --rm frontend yarn run eslint src`
  - Note: The ESLint rule `"import/no-unresolved"` is disabled, because code editors can't find the `node_modules` inside the docker container, and it made everything red. Also, basic testing should catch erroneous imports anyway.
- Flow: `docker-compose run --rm frontend yarn run flow`

#### Run end-to-end browser tests

- **Recommended:** `./scripts/browser_test.sh`
  - Slower, but seeds test DB with random data, and is how tests are run in CI
- `docker-compose run --rm browser_test npx cypress run`
  - Faster, but risks passing due to specific characteristics of local data, then failing in CI.

### Deploy

The app is deployed to Google Cloud with every merge/push to `master`. You can manually deploy in two ways:

- **Recommended:** Manually trigger a build in Travis CI via the "More options" menu.
- Run `./scripts/deploy.sh`, but be careful with which env vars you have in your shell.

## Pro-Tips

- Both `backend` and `frontend` are encapsulated, with their dependencies, in their respective containers, so if you want to take advantage of in-editor linting, autofixing, etc., open your editor from the service directory, not the project directory. Be sure to run terminal commands from the project root, though.

## Troubleshooting

- If, while working on a branch, you're getting a weird error in one of the services unrelated to your current work, try pulling the associated images to make sure you have the latest version.
