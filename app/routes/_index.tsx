import {
  Box,
  Card,
  CardBody,
  Container,
  Flex,
  Heading,
  Text,
} from "@chakra-ui/react";
import { json, LoaderFunctionArgs, MetaFunction } from "@remix-run/node";
import { useLoaderData, useSubmit, Form } from "@remix-run/react";
import max from "lodash/max";

import MetricsTable from "../components/MetricsTable";
import PredictionsTable from "../components/PredictionsTable";
import {
  RoundPrediction,
  fetchRoundPredictions,
  Metrics,
  fetchRoundMetrics,
} from "../.server/predictionService";
import {
  fetchLatestPredictedRound,
  fetchSeasons,
} from "~/.server/seasonService";
import SeasonSelect, { CURRENT_SEASON_PARAM } from "~/components/SeasonSelect";

export const meta: MetaFunction = () => {
  return [
    { title: "Tipresias: A footy-tipping machine-learning model" },
    {
      name: "description",
      content: "Footy tipping tables and charts for the Tipresias model",
    },
  ];
};

export const loader = async ({ request }: LoaderFunctionArgs) => {
  const seasonYears = await fetchSeasons();
  const url = new URL(request.url);
  const currentSeasonYear =
    parseInt(url.searchParams.get(CURRENT_SEASON_PARAM) || "") ||
    max(seasonYears);
  if (!currentSeasonYear) throw Error("No season data found");

  const currentRound = await fetchLatestPredictedRound(currentSeasonYear);
  const predictions: RoundPrediction[] = await fetchRoundPredictions(
    currentSeasonYear
  );
  const metrics: Metrics = await fetchRoundMetrics(currentSeasonYear);

  return json({
    currentRound,
    predictions,
    metrics,
    currentSeasonYear,
    seasonYears,
  });
};

export default function Index() {
  const { currentRound, predictions, metrics, seasonYears, currentSeasonYear } =
    useLoaderData<typeof loader>();
  const submit = useSubmit();

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
          {seasonYears && (
            <Form style={{ padding: "1rem" }}>
              <SeasonSelect
                submit={submit}
                seasonYears={seasonYears}
                currentSeasonYear={currentSeasonYear}
              />
            </Form>
          )}
          {predictions && currentSeasonYear && currentRound && (
            <Card marginTop="1rem" marginBottom="1rem">
              <CardBody>
                <PredictionsTable
                  currentRound={currentRound}
                  currentSeason={currentSeasonYear}
                  predictions={predictions}
                />
              </CardBody>
            </Card>
          )}
          <Card marginTop="1rem" marginBottom="1rem" width="100%">
            <CardBody>
              {metrics && currentSeasonYear && (
                <MetricsTable metrics={metrics} season={currentSeasonYear} />
              )}
            </CardBody>
          </Card>
        </Flex>
      </Box>
    </div>
  );
}
