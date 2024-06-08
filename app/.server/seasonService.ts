import * as R from "ramda";

import { season, sqlQuery } from "./db";

export interface Season {
  id: number;
  year: number;
}

export interface Round {
  roundNumber: number;
}

export const fetchSeasons = () =>
  R.pipe(
    season.findMany,
    R.andThen(R.map(R.prop("year")))
  )({ orderBy: { year: "asc" } });

const buildPredictedRoundsQuery = (seasonYear: number) => `
  SELECT DISTINCT("Match"."roundNumber") FROM "Match"
  INNER JOIN "Season" ON "Season".id = "Match"."seasonId"
  INNER JOIN "Prediction" ON "Prediction"."matchId" = "Match".id
  WHERE "Season".year = ${seasonYear}
  ORDER BY "Match"."roundNumber" ASC
`;

export const fetchPredictedRoundNumbers = (seasonYear: number) =>
  R.pipe(
    buildPredictedRoundsQuery,
    sqlQuery<Round[]>,
    R.andThen(R.map(R.prop("roundNumber")))
  )(seasonYear);
