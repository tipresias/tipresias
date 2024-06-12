# Tipresias

> I Tipresias, old bot with dusty cores<br>
> Perceived the match, and foretold the score—<br>
> I too awaited the fanatics' roar.<br>

Child of [Footy Tipper](https://github.com/cfranklin11/footy-tipper), Tipresias, has, like Zeus before it, arisen to vanquish its father and claim its throne as the sovereign of AFL footy tipping models.

~~Check out the site, with a dashboard for model performance, at [tipresias.net](http://www.tipresias.net).~~ (Currently under construction)

## Running things

### Setup

- Install NVM
- Run `nvm install`
- Install Docker
- Install direnv
- Run `mv .env.example .env` and update env var values
- Run `npm install`
- Run `docker-compose up -d`
- Load data dump with `docker-compose exec db psql -f tipresias/$DATA_DUMP_FILEPATH
- Run `npx prisma db pull`
- Run `npx prisma generate`
- Run `npx prisma migrate deploy`

### Run the app

- Run `docker-compouse up -d`
- Run `npm run dev`
- Navigate to `localhost:5173`.

### A note on architecture

- `tipresias` is composed of multiple micro-services: [`bird-signs`](https://github.com/tipresias/bird-signs) for raw data, [`augury`](https://github.com/tipresias/augury) for machine-learning functionality (i.e. generating model predictions).

### Testing

- Unit tests: `npm run test`
- Linting: `npm run lint`
- Typechecking: `npm run typecheck`

### Deploy

The app is deployed to Vercel with every merge/push to `main`.
