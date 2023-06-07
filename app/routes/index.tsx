import { Box, Container, Flex, Heading, Text } from "@chakra-ui/react";
import { json } from "@remix-run/node";
import { useLoaderData } from "@remix-run/react";
import MetricsTable from "~/components/MetricsTable";

import PredictionsTable from "~/components/PredictionsTable";

export const loader = async () => {
  return json({
    currentRound: 42,
    predictions: new Array(9).fill(null).map((_, i) => ({
      winner: `Team ${i + 1}`,
      loser: `Team ${-i - 1}`,
      margin: i ** 2,
      wasCorrect: i === 0 ? null : Boolean(i % 2),
    })),
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
    <div style={{ fontFamily: "system-ui, sans-serif", lineHeight: "1.4" }}>
      <Container centerContent={true} padding="2rem">
        <Heading as="h1">Tipresias</Heading>
        <Text>A footy-tipping machine-learning model</Text>
      </Container>
      <Flex alignItems="start" justifyContent="space-around" flexWrap="wrap">
        <Box padding="1rem">
          {predictions && (
            <PredictionsTable
              currentRound={currentRound}
              predictions={predictions}
            />
          )}
        </Box>
        <Box padding="1rem">
          {metrics && <MetricsTable metrics={metrics} season={currentSeason} />}
        </Box>
      </Flex>
    </div>
  );
}
