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
import { PrismaClient } from "@prisma/client";
import * as R from "ramda";

import MetricsTable from "../components/MetricsTable";
import PredictionsTable, { Prediction } from "../components/PredictionsTable";

interface RoundPredictionRecord {
  predicted_winner_name: string;
  predicted_margin: number | null;
  predicted_win_probability: number | null;
  is_correct: boolean | null;
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
  const prisma = new PrismaClient();
  const predictions: Prediction[] = await R.pipe(
    () => prisma.$queryRaw<RoundPredictionRecord[]>`
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
    GROUP BY principal_predictions.predicted_winner_name, principal_predictions.is_correct;
  `,
    R.andThen(
      R.map<RoundPredictionRecord, Prediction>(
        ({
          predicted_winner_name,
          predicted_margin,
          predicted_win_probability,
          is_correct,
        }) => ({
          predictedWinnerName: predicted_winner_name,
          predictedMargin: predicted_margin,
          predictedWinProbability: predicted_win_probability,
          isCorrect: is_correct,
        })
      )
    )
  )();

  return json({
    currentRound: 42,
    predictions,
    metrics: [
      { name: "Total Tips", value: "42" },
      { name: "MAE", value: "21.2" },
      { name: "Accuracy", value: "84.8%" },
    ],
    currentSeason: 2023,
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
          {predictions && (
            <Card marginTop="1rem" marginBottom="1rem">
              <CardBody>
                <PredictionsTable
                  currentRound={currentRound}
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
