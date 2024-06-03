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

const ROUND_PREDICTIONS_SQL = `
  WITH "latestPredictedMatch" AS (
    SELECT "Match".id, "Match"."roundNumber", EXTRACT(YEAR FROM "Match"."startDateTime") AS year
    FROM "Match"
    INNER JOIN "Prediction" ON "Prediction"."matchId" = "Match".id
    ORDER BY "Match"."startDateTime" DESC
    LIMIT 1
  ),
  "principalPrediction" AS (
    SELECT "Prediction"."matchId", "Team".name AS "predictedWinnerName", "Prediction"."isCorrect" FROM "Prediction"
    INNER JOIN "Team" ON "Team".id = "Prediction"."predictedWinnerId"
    INNER JOIN "MlModel" ON "MlModel".id = "Prediction"."mlModelId"
    WHERE "MlModel"."isPrincipal" IS TRUE
  )
  SELECT
    "principalPrediction"."predictedWinnerName",
    MAX("Prediction"."predictedMargin") AS "predictedMargin",
    MAX("Prediction"."predictedWinProbability") AS "predictedWinProbability",
    "principalPrediction"."isCorrect"
  FROM "Prediction"
  INNER JOIN "Match" ON "Match".id = "Prediction"."matchId"
  INNER JOIN "MlModel" ON "MlModel".id = "Prediction"."mlModelId"
  INNER JOIN "principalPrediction" ON "principalPrediction"."matchId" = "Prediction"."matchId"
  WHERE "Match"."roundNumber" = (SELECT "latestPredictedMatch"."roundNumber" FROM "latestPredictedMatch")
  AND EXTRACT(YEAR FROM "Match"."startDateTime") = (SELECT "latestPredictedMatch".year FROM "latestPredictedMatch")
  AND "MlModel"."usedInCompetitions" IS TRUE
  GROUP BY "principalPrediction"."predictedWinnerName", "principalPrediction"."isCorrect", "Match"."startDateTime"
  ORDER BY "Match"."startDateTime" DESC
`;

export const fetchRoundPredictions = () =>
  sqlQuery<RoundPrediction[]>(ROUND_PREDICTIONS_SQL);

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
