# Tipresias

> I Tipresias, old bot with dusty cores<br>
> Perceived the match, and foretold the score—<br>
> I too awaited the fanatics' roar.<br>

Child of [Footy Tipper](https://github.com/cfranklin11/footy-tipper), Tipresias, has, like Zeus before it, arisen to vanquish its father and claim its throne as the sovereign of AFL footy tipping models.

~~Check out the site, with a dashboard for model performance, at [tipresias.net](http://www.tipresias.net).~~ (Currently under construction)

## Running things

### Setup

#### Install dependencies

- Run `npm install`

### Run the app

- Run `npm run dev`
- Navigate to `localhost:3000`.

### A note on architecture

- `tipresias` is composed of multiple micro-services: [`bird-signs`](https://github.com/tipresias/bird-signs) for raw data, [`augury`](https://github.com/tipresias/augury) for machine-learning functionality (i.e. generating model predictions).

### Testing

- Unit tests: `npm run test`
- e2e tests: `npm run test:e2e:run`
- Linting: `npm run lint`
- Typechecking: `npm run typecheck`

### Deploy

The app is deployed to AWS with every merge/push to `main`.
