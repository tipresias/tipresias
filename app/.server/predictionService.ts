import * as R from "ramda";

import { sqlQuery } from "./db";

export interface RoundPredictionRecord {
  predicted_winner_name: string;
  predicted_margin: number | null;
  predicted_win_probability: number | null;
  is_correct: boolean | null;
}

export interface Prediction {
  predictedWinnerName: string;
  predictedMargin: number | null;
  predictedWinProbability: number | null;
  isCorrect: boolean | null;
}

export interface MetricsRecord {
  total_tips: number | null;
  accuracy: number | null;
  mae: number | null;
  bits: number | null;
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
const convertPredictionKeysToCamelCase = ({
  predicted_winner_name,
  predicted_margin,
  predicted_win_probability,
  is_correct,
}: RoundPredictionRecord): Prediction => ({
  predictedWinnerName: predicted_winner_name,
  predictedMargin: predicted_margin,
  predictedWinProbability: predicted_win_probability,
  isCorrect: is_correct,
});

export const fetchRoundPredictions = () =>
  R.pipe(
    sqlQuery<RoundPredictionRecord[]>,
    R.andThen(R.map(convertPredictionKeysToCamelCase))
  )(ROUND_PREDICTIONS_SQL);

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
const convertMetricKeysToCamelCase = ({
  total_tips,
  accuracy,
  mae,
  bits,
}: MetricsRecord) => ({
  totalTips: total_tips,
  accuracy,
  mae,
  bits,
});
export const fetchRoundMetrics = () =>
  R.pipe(
    sqlQuery<MetricsRecord[]>,
    R.andThen(R.map<MetricsRecord, Metrics>(convertMetricKeysToCamelCase)),
    R.andThen(R.head<Metrics>),
    R.andThen(R.defaultTo(BLANK_METRICS))
  )(SEASON_METRICS_SQL);
