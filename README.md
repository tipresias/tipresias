# Tipresias

[![Build Status](https://travis-ci.com/tipresias/tipresias.svg?branch=master)](https://travis-ci.com/tipresias/tipresias)

> I Tipresias, old bot with dusty cores<br>
> Perceived the match, and foretold the score—<br>
> I too awaited the fanatics' roar.<br>

Child of [Footy Tipper](https://github.com/cfranklin11/footy-tipper), Tipresias, has, like Zeus before it, arisen to vanquish its father and claim its throne as the master of AFL footy tipping models.

## Running things

### Setup

- To manage environemnt variables:
  - Install [`direnv`](https://direnv.net/)
  - Add `eval "$(direnv hook bash)"` to the bottom of `~/.bashrc`
  - Run `direnv allow .` inside the project directory
- Create the `node_modules` volume: `docker volume create --name=node_modules`
- To build and run the app: `docker-compose up --build`
- Migrate the DB: `docker-compose run --rm backend python3 manage.py migrate`
- Generate raw data for `data_science` functionality: `docker-compose run --rm data_science ./scripts/generate_data_sets.sh`
- Seed the DB: `docker-compose run --rm backend python3 manage.py seed_db` (this takes a very long time, so it's recommended that you reset the DB as described below if possible)
- Reset the DB to match production: `./scripts/reset_local_db_to_prod.sh`
  - This requires ability to `ssh` into the prod server (i.e. you must have been added as a user to the server by an admin)
  - `PROD_USER` and `IP_ADDRESS` environment variables have to be set in the current bash session, and their values have to be applicable to the relevant server
- To interact with production resources, install the Google Cloud SDK:
  - `brew cask install google-cloud-sdk` (on Mac)
  - `gcloud auth login` (redirects you to log into your Google account in the browser)
  - `gcloud config set project ${PROJECT_ID}`
- To `ssh` into the server, run `./scripts/ssh.sh`.
- To run the tipping command, run `./scripts/tip.sh`.

### Run the app

- `docker-compose up`
- Navigate to `localhost:3000`.

### A note on architecture

- `tipresias` depends on two micro-services: [`bird-signs`](https://github.com/tipresias/bird-signs) for raw data and [`augury`](https://github.com/tipresias/augury) for machine-learning functionality (i.e. generating model predictions). In the dev environment, this is managed via docker-compose, which uses the images of these services; in production, the app calls relevant Google Cloud functions. If one of these services isn't working on local, try pulling the latest image, as something might have changed.

### Testing

#### Run Python tests

- `docker-compose run --rm backend python3 -Wi manage.py test`
- Linting: `docker-compose run --rm backend pylint --disable=R <python modules you want to lint>`
  - Note: `-d=R` disables refactoring checks for quicker, less-opinionated linting. Remove that option if you want to include those checks.
- Type checking: `docker-compsoe run mypy <python modules you want to check>`

#### Run Javascript tests

- `docker-compose run --rm frontend yarn run test:unit`
- Linting: `docker-compose run --rm frontend yarn run eslint src`
  - Note: The ESLint rule `"import/no-unresolved"` is disabled, because code editors can't find the `node_modules` inside the docker container, and it made everything red. Also, basic testing should catch erroneous imports anyway.
- Flow: `docker-compose run --rm frontend yarn run flow`

#### Run end-to-end browser tests

- `docker-compose run --rm browser npx cypress run`

### Deploy

- Deploy app to DigitalOcean:

  - Merge a pull request into `master`
  - Manually trigger a deploy:
    - In the Travis dashboard, navigate to the tipresias repository.
    - Under 'More Options', trigger a build on `master`.
    - This will build the image, run tests, and deploy to DigitalOcean.

## Pro-Tips

- Both `backend` and `frontend` are encapsulated, with their dependencies, in their respective containers, so if you want to take advantage of in-editor linting, autofixing, etc., open your editor from the service directory, not the project directory. Be sure to run terminal commands from the project root, though.

## Troubleshooting

- If, while working on a branch, you're getting a weird error in one of the services unrelated to your current work, try pulling the associated images to make sure you have the latest version.
