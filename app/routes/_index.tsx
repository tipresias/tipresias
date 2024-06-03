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

import MetricsTable from "../components/MetricsTable";
import PredictionsTable from "../components/PredictionsTable";
import {
  RoundPrediction,
  fetchRoundPredictions,
  Metrics,
  fetchRoundMetrics,
} from "../.server/predictionService";
import { sqlQuery } from "../.server/db";

interface Round {
  roundNumber: number;
  season: number;
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
  const PREDICTED_ROUND_SQL = `
    SELECT "Match"."roundNumber", EXTRACT(YEAR FROM "Match"."startDateTime") AS season
    FROM "Match"
    INNER JOIN "Prediction" ON "Prediction"."matchId" = "Match".id
    ORDER BY "Match"."startDateTime" DESC
    LIMIT 1
  `;
  const predictedRound = (await sqlQuery<Round[]>(PREDICTED_ROUND_SQL))[0];
  const predictions: RoundPrediction[] = await fetchRoundPredictions();
  const metrics: Metrics = await fetchRoundMetrics();

  return json({
    currentRound: predictedRound.roundNumber,
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
