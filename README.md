# Tipresias

[![Build Status](https://travis-ci.com/tipresias/tipresias.svg?branch=main)](https://travis-ci.com/tipresias/tipresias)
<a href="https://codeclimate.com/github/tipresias/tipresias/maintainability"><img src="https://api.codeclimate.com/v1/badges/b6a40f7f72b307763b88/maintainability" /></a>
<a href="https://codeclimate.com/github/tipresias/tipresias/test_coverage"><img src="https://api.codeclimate.com/v1/badges/b6a40f7f72b307763b88/test_coverage" /></a>

> I Tipresias, old bot with dusty cores<br>
> Perceived the match, and foretold the score—<br>
> I too awaited the fanatics' roar.<br>

Child of [Footy Tipper](https://github.com/cfranklin11/footy-tipper), Tipresias, has, like Zeus before it, arisen to vanquish its father and claim its throne as the sovereign of AFL footy tipping models.

Check out the site, with a dashboard for model performance, at [tipresias.net](http://www.tipresias.net).

## Running things

### Setup

#### Install dependencies

- Install [`direnv`](https://direnv.net/)
  - Loads env vars from `.env`, which is convenient
- Install Docker
- Optional: install `doctl`, the DigitalOcean CLI tool (just a convenient way to interact with DO resources)

#### Set up development environment and the app itself

- To manage environment variables:
  - Add `eval "$(direnv hook bash)"` to the bottom of `~/.bashrc`
  - Run `direnv allow .` inside the project directory
- To set up the app:
  - Create the `node_modules` volume: `docker volume create tipresias_node_modules`
  - To build and run the app: `docker-compose up --build`

#### Seed the database

**Recommended:** `./scripts/set_local_db_to_prod.sh`
  - Downloads the production database and loads it on local

Seed the DB with raw data:
  - Migrate the DB: `docker-compose run --rm backend python3 manage.py migrate`
  - Run `docker-compose run --rm backend python3 manage.py seed_db`
    - This takes a very long time, so it's recommended that you reset the DB as described below if possible

### Run the app

- `docker-compose up`
- Navigate to `localhost:3000`.

#### Useful commands

- To `ssh` into the server, run `./scripts/ssh.sh`.
  - To run a command instead of opening a bash session, you can add a string as an argument.
- To run the tipping command, run `./scripts/tip.sh`.

### A note on architecture

- `tipresias` depends on two micro-services: [`bird-signs`](https://github.com/tipresias/bird-signs) for raw data and [`augury`](https://github.com/tipresias/augury) for machine-learning functionality (i.e. generating model predictions).

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

- **Recommended:** `./scripts/browser_tests.sh`
  - Slower, but seeds test DB with random data, and is how tests are run in CI
- `docker-compose run --rm browser_test npx cypress run`
  - Faster, but risks passing due to specific characteristics of local data, then failing in CI.

### Deploy

The app is deployed to Google Cloud with every merge/push to `main`. You can manually deploy in two ways:

- **Recommended:** Manually trigger a build in Travis CI via the "More options" menu.
- Run `./scripts/deploy.sh`, but be careful with which env vars you have in your shell.

## Pro-Tips

- Both `backend` and `frontend` are encapsulated, with their dependencies, in their respective containers, so if you want to take advantage of in-editor linting, autofixing, etc., open your editor from the service directory, not the project directory. Be sure to run terminal commands from the project root, though.

## Troubleshooting

- If you get errors in `frontend` related to missing packages, even after building a new image, try the following to clear its `node_modules` directory:
  - `docker-compose stop`
  - `docker container rm tipresias_frontend_1 tipresias_storybook_1`
  - `docker volume rm tipresias_node_modules`
  - `rm -rf frontend/node_modules`
  - `docker volume create tipresias_node_modules`
  - `docker-compose build --no-cache frontend`
