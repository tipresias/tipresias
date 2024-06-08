import * as R from "ramda";

import { season, sqlQuery } from "./db";

export interface Season {
  id: number;
  year: number;
}

export interface Round {
  number: number | null;
}

const BLANK_ROUND: Round = {
  number: null,
};

export const fetchSeasons = () =>
  R.pipe(season.findMany, R.andThen(R.map(R.prop("year"))))();

const buildLatestPredictedRoundQuery = (season: number) => `
  SELECT MAX("Match"."roundNumber") AS number FROM "Match"
  INNER JOIN "Season" ON "Season".id = "Match"."seasonId"
  INNER JOIN "Prediction" ON "Prediction"."matchId" = "Match".id
  WHERE "Season".year = ${season}
`;

export const fetchLatestPredictedRound = (seasonYear: number) =>
  R.pipe(
    buildLatestPredictedRoundQuery,
    sqlQuery<Round[]>,
    R.andThen(R.head<Round>),
    R.andThen(R.defaultTo(BLANK_ROUND)),
    R.andThen(R.prop("number"))
  )(seasonYear);
