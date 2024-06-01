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
  Prediction,
  fetchRoundPredictions,
  Metrics,
  fetchRoundMetrics,
} from "../.server/predictionService";
import { buildSql, sqlQuery } from "../.server/db";

interface Round {
  round_number: number;
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
  const predictedRoundSql = buildSql`
    SELECT server_match.round_number, EXTRACT(YEAR FROM server_match.start_date_time) AS season
    FROM server_match
    INNER JOIN server_prediction ON server_prediction.match_id = server_match.id
    ORDER BY server_match.start_date_time DESC
    LIMIT 1
  `;
  const predictedRound = (await sqlQuery<Round[]>(predictedRoundSql))[0];
  const predictions: Prediction[] = await fetchRoundPredictions();
  const metrics: Metrics = await fetchRoundMetrics();

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
