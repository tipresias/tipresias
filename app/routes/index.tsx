import { Container, Flex, Heading, Text } from "@chakra-ui/react";
import { json } from "@remix-run/node";
import { useLoaderData } from "@remix-run/react";

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
  });
};

export default function Index() {
  const { currentRound, predictions } = useLoaderData<typeof loader>();

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", lineHeight: "1.4" }}>
      <Container centerContent={true} style={{ padding: "2rem" }}>
        <Heading as="h1">Tipresias</Heading>
        <Text>A footy-tipping machine-learning model</Text>
      </Container>
      <Flex alignItems="center" flexDirection="column">
        {predictions && (
          <PredictionsTable
            currentRound={currentRound}
            predictions={predictions}
          />
        )}
      </Flex>
    </div>
  );
}
