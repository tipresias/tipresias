import * as R from "ramda";

import { sqlQuery } from "./db";

export interface RoundPrediction {
  predictedWinnerName: string;
  predictedMargin: number | null;
  predictedWinProbability: number | null;
  isCorrect: boolean | null;
}

export interface SeasonMetrics {
  totalTips: number | null;
  accuracy: number | null;
  mae: number | null;
  bits: number | null;
}

const buildRoundPredictionQuery = (seasonYear: number, roundNumber: number) => `
  WITH "PrincipalPrediction" AS (
    SELECT "Prediction".*, "Team".name AS "predictedWinnerName" FROM "Prediction"
    INNER JOIN "Team" ON "Team".id = "Prediction"."predictedWinnerId"
    INNER JOIN "MlModel" ON "MlModel".id = "Prediction"."mlModelId"
    INNER JOIN "MlModelSeason" ON "MlModelSeason"."mlModelId" = "MlModel".id
    INNER JOIN "Season" ON "Season".id = "MlModelSeason"."seasonId"
    WHERE "MlModelSeason"."isPrincipal" IS TRUE
    AND "Season".year = ${seasonYear}
  ),
  "SecondaryPrediction" AS (
    SELECT
    "Prediction"."matchId",
    CASE
      WHEN "Prediction"."predictedWinnerId" = "PrincipalPrediction"."predictedWinnerId"
      THEN "Prediction"."predictedWinProbability"
      ELSE 1 - "Prediction"."predictedWinProbability"
    END AS "predictedWinProbability",
    CASE
      WHEN "Prediction"."predictedWinnerId" = "PrincipalPrediction"."predictedWinnerId"
      THEN "Prediction"."predictedMargin"
      ELSE -1 * "Prediction"."predictedMargin"
    END AS "predictedMargin"
    FROM "Prediction"
    INNER JOIN "MlModel" ON "MlModel".id = "Prediction"."mlModelId"
    INNER JOIN "MlModelSeason" ON "MlModelSeason"."mlModelId" = "MlModel".id
    INNER JOIN "Season" ON "Season".id = "MlModelSeason"."seasonId"
    INNER JOIN "PrincipalPrediction" ON "PrincipalPrediction"."matchId" = "Prediction"."matchId"
    WHERE "MlModelSeason"."isPrincipal" IS FALSE
    AND "MlModelSeason"."isUsedInCompetitions" IS TRUE
    AND "Season".year = ${seasonYear}
  )
  SELECT
    "PrincipalPrediction"."predictedWinnerName",
    COALESCE("PrincipalPrediction"."predictedMargin", "SecondaryPrediction"."predictedMargin") AS "predictedMargin",
    COALESCE("PrincipalPrediction"."predictedWinProbability", "SecondaryPrediction"."predictedWinProbability") AS "predictedWinProbability",
    "PrincipalPrediction"."isCorrect"
  FROM "Match"
  INNER JOIN "Season" ON "Season".id = "Match"."seasonId"
  INNER JOIN "PrincipalPrediction" ON "PrincipalPrediction"."matchId" = "Match".id
  LEFT OUTER JOIN "SecondaryPrediction" ON "SecondaryPrediction"."matchId" = "Match".id
  WHERE "Match"."roundNumber" = ${roundNumber}
  AND "Season".year = ${seasonYear}
  ORDER BY "Match"."startDateTime" DESC
`;

export const fetchRoundPredictions = (
  seasonYear: number,
  roundNumber: number
) =>
  R.pipe(buildRoundPredictionQuery, sqlQuery<RoundPrediction[]>)(
    seasonYear,
    roundNumber
  );

const buildSeasonMetricsQuery = (seasonYear: number) => `
  SELECT
    SUM("Prediction"."isCorrect"::int) FILTER(WHERE "MlModelSeason"."isPrincipal" IS TRUE)::int AS "totalTips",
    AVG("Prediction"."isCorrect"::int) FILTER(WHERE "MlModelSeason"."isPrincipal" IS TRUE)::float AS accuracy,
    AVG(
      CASE
        WHEN "Prediction"."isCorrect" IS TRUE
          THEN ABS("Match".margin - "Prediction"."predictedMargin")
        ELSE
          "Match".margin + "Prediction"."predictedMargin"
        END
    ) FILTER(WHERE "Prediction"."predictedMargin" IS NOT NULL) AS mae,
    SUM(
      (
        CASE
          WHEN "Match".margin = 0
            THEN 1 + (0.5 * LOG(2, ("Prediction"."predictedWinProbability" * (1 - "Prediction"."predictedWinProbability"))::numeric))
          WHEN "Match".margin <> 0 AND "Prediction"."isCorrect" IS TRUE
            THEN 1 + LOG(2, "Prediction"."predictedWinProbability"::numeric)
          WHEN "Prediction"."isCorrect" IS FALSE
            THEN 1 + LOG(2, (1 - "Prediction"."predictedWinProbability")::numeric)
          END
        )::float
    ) FILTER(WHERE "Prediction"."predictedWinProbability" IS NOT NULL) AS bits
  FROM "Prediction"
  INNER JOIN "MlModel" ON "MlModel".id = "Prediction"."mlModelId"
  INNER JOIN "Match" ON "Match".id = "Prediction"."matchId"
  INNER JOIN "Season" ON "Season".id = "Match"."seasonId"
  INNER JOIN "MlModelSeason" ON "MlModelSeason"."mlModelId" = "MlModel".id AND "MlModelSeason"."seasonId" = "Season".id
  WHERE "MlModelSeason"."isUsedInCompetitions" IS TRUE
  AND "Prediction"."isCorrect" IS NOT NULL
  AND "Season".year = ${seasonYear}
`;
const BLANK_SEASON_METRICS: SeasonMetrics = {
  totalTips: null,
  accuracy: null,
  mae: null,
  bits: null,
};
export const fetchSeasonMetrics = (seasonYear: number) =>
  R.pipe(
    buildSeasonMetricsQuery,
    sqlQuery<SeasonMetrics[]>,
    R.andThen(R.head<SeasonMetrics>),
    R.andThen(R.defaultTo(BLANK_SEASON_METRICS))
  )(seasonYear);
