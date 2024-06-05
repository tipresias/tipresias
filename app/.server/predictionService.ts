import * as R from "ramda";

import { sqlQuery } from "./db";

export interface RoundPrediction {
  predictedWinnerName: string;
  predictedMargin: number | null;
  predictedWinProbability: number | null;
  isCorrect: boolean | null;
}

export interface Metrics {
  totalTips: number | null;
  accuracy: number | null;
  mae: number | null;
  bits: number | null;
}

const buildRoundPredictionQuery = (seasonYear: number) => `
  WITH "LatestPredictedMatch" AS (
    SELECT "Match".id, "Match"."roundNumber", "Season".year
    FROM "Match"
    INNER JOIN "Prediction" ON "Prediction"."matchId" = "Match".id
    INNER JOIN "Season" ON "Season".id = "Match"."seasonId"
    WHERE "Season".year = ${seasonYear}
    ORDER BY "Match"."startDateTime" DESC
    LIMIT 1
  ),
  "PrincipalPrediction" AS (
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
  WHERE "Match"."roundNumber" = (SELECT "LatestPredictedMatch"."roundNumber" FROM "LatestPredictedMatch")
  AND "Season".year = ${seasonYear}
  ORDER BY "Match"."startDateTime" DESC
`;

export const fetchRoundPredictions = (seasonYear: number) =>
  R.pipe(buildRoundPredictionQuery, sqlQuery<RoundPrediction[]>)(seasonYear);

const SEASON_METRICS_SQL = `
  WITH "latestPredictedMatch" AS (
    SELECT "Match".id, "Match"."roundNumber", EXTRACT(YEAR FROM "Match"."startDateTime") AS year
    FROM "Match"
    INNER JOIN "Prediction" ON "Prediction"."matchId" = "Match".id
    ORDER BY "Match"."startDateTime" DESC
    LIMIT 1
  )
  SELECT
    SUM("Prediction"."isCorrect"::int) FILTER(WHERE "MlModel"."isPrincipal" IS TRUE)::int AS "totalTips",
    AVG("Prediction"."isCorrect"::int) FILTER(WHERE "MlModel"."isPrincipal" IS TRUE) AS accuracy,
    AVG(ABS("Match".margin + ("Prediction"."predictedMargin" * "Prediction"."isCorrect"::int + "Prediction"."predictedMargin" * ("Prediction"."isCorrect"::int - 1)) * -1))
      FILTER(WHERE "Prediction"."predictedMargin" IS NOT NULL) AS mae,
    SUM(
      CASE
        WHEN "Match".margin = 0
          THEN 1 + (0.5 * LOG(2, ("Prediction"."predictedWinProbability" * (1 - "Prediction"."predictedWinProbability"))::numeric))
        WHEN "Prediction"."isCorrect" IS TRUE
          THEN 1 + LOG(2, "Prediction"."predictedWinProbability"::numeric)
        WHEN "Prediction"."isCorrect" IS FALSE
          THEN 1 + LOG(2, (1 - "Prediction"."predictedWinProbability")::numeric)
        END
    ) FILTER(WHERE "Prediction"."predictedWinProbability" IS NOT NULL) AS bits

  FROM "Prediction"
  INNER JOIN "MlModel" ON "MlModel".id = "Prediction"."mlModelId"
  INNER JOIN "Match" ON "Match".id = "Prediction"."matchId"
  WHERE "MlModel"."usedInCompetitions" IS TRUE
  AND "Prediction"."isCorrect" IS NOT NULL
  AND EXTRACT(YEAR FROM "Match"."startDateTime") = (SELECT "latestPredictedMatch".year FROM "latestPredictedMatch")
`;
const BLANK_METRICS: Metrics = {
  totalTips: null,
  accuracy: null,
  mae: null,
  bits: null,
};
export const fetchRoundMetrics = () =>
  R.pipe(
    sqlQuery<Metrics[]>,
    R.andThen(R.head<Metrics>),
    R.andThen(R.defaultTo(BLANK_METRICS))
  )(SEASON_METRICS_SQL);
