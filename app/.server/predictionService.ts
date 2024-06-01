import * as R from "ramda";

import { buildSql, sqlQuery } from "./db";

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

const BLANK_METRICS: Metrics = {
  totalTips: null,
  accuracy: null,
  mae: null,
  bits: null,
};

const roundPredictionsSql = buildSql`
  WITH latest_predicted_match AS (
    SELECT server_match.id, server_match.round_number, EXTRACT(YEAR FROM server_match.start_date_time) AS year
    FROM server_match
    INNER JOIN server_prediction ON server_prediction.match_id = server_match.id
    ORDER BY server_match.start_date_time DESC
    LIMIT 1
  ),
  principal_predictions AS (
    SELECT server_prediction.match_id, server_team.name AS predicted_winner_name, server_prediction.is_correct FROM server_prediction
    INNER JOIN server_team ON server_team.id = server_prediction.predicted_winner_id
    INNER JOIN server_mlmodel ON server_mlmodel.id = server_prediction.ml_model_id
    WHERE server_mlmodel.is_principal IS TRUE
  )
  SELECT
    principal_predictions.predicted_winner_name,
    MAX(server_prediction.predicted_margin) AS predicted_margin,
    MAX(server_prediction.predicted_win_probability) AS predicted_win_probability,
    principal_predictions.is_correct
  FROM server_prediction
  INNER JOIN server_match ON server_match.id = server_prediction.match_id
  INNER JOIN server_mlmodel ON server_mlmodel.id = server_prediction.ml_model_id
  INNER JOIN principal_predictions ON principal_predictions.match_id = server_prediction.match_id
  WHERE server_match.round_number = (SELECT latest_predicted_match.round_number FROM latest_predicted_match)
  AND EXTRACT(YEAR FROM server_match.start_date_time) = (SELECT latest_predicted_match.year FROM latest_predicted_match)
  AND server_mlmodel.used_in_competitions IS TRUE
  GROUP BY principal_predictions.predicted_winner_name, principal_predictions.is_correct, server_match.start_date_time
  ORDER BY server_match.start_date_time DESC
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
  )(roundPredictionsSql);

const metricsSql = buildSql`
  WITH latest_predicted_match AS (
    SELECT server_match.id, server_match.round_number, EXTRACT(YEAR FROM server_match.start_date_time) AS year
    FROM server_match
    INNER JOIN server_prediction ON server_prediction.match_id = server_match.id
    ORDER BY server_match.start_date_time DESC
    LIMIT 1
  )
  SELECT
    SUM(server_prediction.is_correct::int) FILTER(WHERE server_mlmodel.is_principal IS TRUE)::int AS total_tips,
    AVG(server_prediction.is_correct::int) FILTER(WHERE server_mlmodel.is_principal IS TRUE) AS accuracy,
    AVG(ABS(server_match.margin + (server_prediction.predicted_margin * server_prediction.is_correct::int + server_prediction.predicted_margin * (server_prediction.is_correct::int - 1)) * -1))
      FILTER(WHERE server_prediction.predicted_margin IS NOT NULL) AS mae,
    SUM(
      CASE
        WHEN server_match.margin = 0
          THEN 1 + (0.5 * LOG(2, (server_prediction.predicted_win_probability * (1 - server_prediction.predicted_win_probability))::numeric))
        WHEN server_prediction.is_correct IS TRUE
          THEN 1 + LOG(2, server_prediction.predicted_win_probability::numeric)
        WHEN server_prediction.is_correct IS FALSE
          THEN 1 + LOG(2, (1 - server_prediction.predicted_win_probability)::numeric)
        END
    ) FILTER(WHERE server_prediction.predicted_win_probability IS NOT NULL) AS bits

  FROM server_prediction
  INNER JOIN server_mlmodel ON server_mlmodel.id = server_prediction.ml_model_id
  INNER JOIN server_match ON server_match.id = server_prediction.match_id
  WHERE server_mlmodel.used_in_competitions IS TRUE
  AND server_prediction.is_correct IS NOT NULL
  AND EXTRACT(YEAR FROM server_match.start_date_time) = (SELECT latest_predicted_match.year FROM latest_predicted_match)
`;
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
  )(metricsSql);
