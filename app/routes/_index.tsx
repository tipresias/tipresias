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
import { useLoaderData, useSubmit, Form, useFetcher } from "@remix-run/react";
import max from "lodash/max";
import * as R from "ramda";

import MetricsTable from "../components/MetricsTable";
import PredictionsTable from "../components/PredictionsTable";
import {
  RoundPrediction,
  fetchRoundMetrics,
  fetchSeasonMetrics,
} from "../.server/predictionService";
import {
  fetchPredictedRoundNumbers,
  fetchSeasons,
} from "~/.server/seasonService";
import SeasonSelect, { CURRENT_SEASON_PARAM } from "~/components/SeasonSelect";
import MetricsChart from "~/components/MetricsChart";

export const meta: MetaFunction = () => {
  return [
    { title: "Tipresias: A footy-tipping machine-learning model" },
    {
      name: "description",
      content: "Footy tipping tables and charts for the Tipresias model",
    },
  ];
};

const getCurrentTemporalValue = (paramValue: string, collection: number[]) =>
  R.pipe(
    parseInt,
    (value) => collection.find((item) => item === value) || max(collection),
    R.tap<number | undefined, number>((value) => {
      if (value === undefined) throw Error("Required data not found");
    })
  )(paramValue);

export const loader = async ({ request }: LoaderFunctionArgs) => {
  const { searchParams } = new URL(request.url);

  const seasonYears = await fetchSeasons();
  const currentSeasonYear = getCurrentTemporalValue(
    searchParams.get(CURRENT_SEASON_PARAM) || "",
    seasonYears
  );
  const roundNumbers = await fetchPredictedRoundNumbers(currentSeasonYear);

  const metrics = await fetchSeasonMetrics(currentSeasonYear);
  const roundMetrics = await fetchRoundMetrics(currentSeasonYear);

  return json({
    roundNumbers,
    metrics,
    currentSeasonYear,
    seasonYears,
    roundMetrics,
  });
};

export default function Index() {
  const {
    roundNumbers,
    metrics,
    seasonYears,
    currentSeasonYear,
    roundMetrics,
  } = useLoaderData<typeof loader>();
  const submit = useSubmit();
  const predictionFetcher = useFetcher<RoundPrediction[]>();

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
          {seasonYears && roundNumbers && currentSeasonYear && (
            <Form style={{ padding: "1rem" }}>
              <SeasonSelect
                submit={submit}
                seasonYears={seasonYears}
                currentSeasonYear={currentSeasonYear}
              />
            </Form>
          )}
          {roundMetrics && (
            <Card marginTop="1rem" marginBottom="1rem" width="100%">
              <CardBody>
                <MetricsChart roundMetrics={roundMetrics} />
              </CardBody>
            </Card>
          )}
          {currentSeasonYear && roundNumbers?.length && (
            <Card marginTop="1rem" marginBottom="1rem">
              <CardBody>
                <PredictionsTable
                  loadData={predictionFetcher.load}
                  roundNumbers={roundNumbers}
                  seasonYear={currentSeasonYear}
                  predictions={predictionFetcher.data || []}
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
