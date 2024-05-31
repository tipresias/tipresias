import {
  Box,
  Card,
  CardBody,
  Container,
  Flex,
  Heading,
  Text,
} from "@chakra-ui/react";
import { json, MetaFunction } from "@remix-run/node";
import { useLoaderData } from "@remix-run/react";
import * as R from "ramda";

import MetricsTable, { Metrics } from "../components/MetricsTable";
import PredictionsTable from "../components/PredictionsTable";
import { Prediction, fetchRoundPredictions } from "~/.server/predictionService";
import { buildSql, sqlQuery } from "~/.server/db";

interface Round {
  round_number: number;
  season: number;
}

interface MetricsRecord {
  total_tips: number | null;
  accuracy: number | null;
  mae: number | null;
  bits: number | null;
}

export const meta: MetaFunction = () => {
  return [
    { title: "Tipresias: A footy-tipping machine-learning model" },
    {
      name: "description",
      content: "Footy tipping tables and charts for the Tipresias model",
    },
  ];
};

export const loader = async () => {
  const predictedRoundSql = buildSql`
    SELECT server_match.round_number, EXTRACT(YEAR FROM server_match.start_date_time) AS season
    FROM server_match
    INNER JOIN server_prediction ON server_prediction.match_id = server_match.id
    ORDER BY server_match.start_date_time DESC
    LIMIT 1
  `;
  const predictedRound = (await sqlQuery<Round[]>(predictedRoundSql))[0];
  const predictions: Prediction[] = await fetchRoundPredictions();
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
  const metrics = (await R.pipe(
    sqlQuery<MetricsRecord[]>,
    R.andThen(
      R.map<MetricsRecord, Metrics>(({ total_tips, accuracy, mae, bits }) => ({
        totalTips: total_tips,
        accuracy,
        mae,
        bits,
      }))
    ),
    R.andThen(R.head<Metrics>)
  )(metricsSql)) || {
    totalTips: null,
    accuracy: null,
    mae: null,
    bits: null,
  };

  return json({
    currentRound: predictedRound.round_number,
    predictions,
    metrics,
    currentSeason: predictedRound.season,
  });
};

export default function Index() {
  const { currentRound, predictions, metrics, currentSeason } =
    useLoaderData<typeof loader>();

  return (
    <div
      style={{
        fontFamily: "system-ui, sans-serif",
        lineHeight: "1.4",
        backgroundColor: "ghostwhite",
      }}
    >
      <Container centerContent={true} padding="2rem">
        <Heading as="h1">Tipresias</Heading>
        <Text>A footy-tipping machine-learning model</Text>
      </Container>
      <Box margin="auto" width="fit-content">
        <Flex alignItems="center" flexWrap="wrap" direction="column">
          {predictions?.length && (
            <Card marginTop="1rem" marginBottom="1rem">
              <CardBody>
                <PredictionsTable
                  currentRound={currentRound}
                  currentSeason={currentSeason}
                  predictions={predictions}
                />
              </CardBody>
            </Card>
          )}
          <Card marginTop="1rem" marginBottom="1rem" width="100%">
            <CardBody>
              {metrics && (
                <MetricsTable metrics={metrics} season={currentSeason} />
              )}
            </CardBody>
          </Card>
        </Flex>
      </Box>
    </div>
  );
}
