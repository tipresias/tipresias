import * as R from "ramda";

import { buildSql, sqlQuery } from "./db";

interface RoundPredictionRecord {
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
const queryRoundPredictions = () =>
  sqlQuery<RoundPredictionRecord[]>(roundPredictionsSql);
const convertKeysToCamelCase = ({
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

export const fetchRoundPredictions = R.pipe(
  queryRoundPredictions,
  R.andThen(R.map(convertKeysToCamelCase))
);
