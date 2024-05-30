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
import { Prediction, fetchRoundPredictions } from "~/.server/predictionService";

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
  const predictions: Prediction[] = await fetchRoundPredictions();

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
