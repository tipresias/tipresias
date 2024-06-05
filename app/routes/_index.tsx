import {
  Box,
  Card,
  CardBody,
  Container,
  Flex,
  FormControl,
  FormLabel,
  Heading,
  Text,
  Select,
} from "@chakra-ui/react";
import { json, LoaderFunctionArgs, MetaFunction } from "@remix-run/node";
import { useLoaderData, Form, useSubmit } from "@remix-run/react";
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

const CURRENT_SEASON_PARAM = "current-season";

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
  const seasons = await fetchSeasons();
  const url = new URL(request.url);
  const currentSeason =
    parseInt(url.searchParams.get(CURRENT_SEASON_PARAM) || "") || max(seasons);
  if (!currentSeason) throw Error("No season data found");

  const currentRound = await fetchLatestPredictedRound(currentSeason);
  const predictions: RoundPrediction[] = await fetchRoundPredictions(
    currentSeason
  );
  const metrics: Metrics = await fetchRoundMetrics();

  return json({
    currentRound,
    predictions,
    metrics,
    currentSeason,
    seasons,
  });
};

export default function Index() {
  const { currentRound, predictions, metrics, seasons, currentSeason } =
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
          <Form>
            <FormControl>
              <FormLabel>Season</FormLabel>
              <Select name={CURRENT_SEASON_PARAM} defaultValue={currentSeason}>
                {seasons.map((season) => (
                  <option
                    key={season}
                    value={season}
                    onClick={(event) => submit(event.currentTarget.form)}
                  >
                    {season}
                  </option>
                ))}
              </Select>
            </FormControl>
          </Form>
          {predictions?.length && currentSeason && currentRound && (
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
              {metrics && currentSeason && (
                <MetricsTable metrics={metrics} season={currentSeason} />
              )}
            </CardBody>
          </Card>
        </Flex>
      </Box>
    </div>
  );
}
