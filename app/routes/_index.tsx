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
import * as R from "ramda";

import MetricsTable from "../components/MetricsTable";
import PredictionsTable from "../components/PredictionsTable";
import {
  fetchRoundMetrics,
  fetchRoundPredictions,
  fetchSeasonMetrics,
} from "../.server/predictionService";
import {
  fetchPredictedRoundNumbers,
  fetchSeasons,
} from "~/.server/seasonService";
import SeasonSelect, { CURRENT_SEASON_PARAM } from "~/components/SeasonSelect";
import RoundSelect, { CURRENT_ROUND_PARAM } from "~/components/RoundSelect";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const CHART_PALETTE = [
  "#E69F00",
  "#56B4E9",
  "#CC79A7",
  "#009E73",
  "#0072B2",
  "#D55E00",
  "#F0E442",
];

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
  const currentRoundNumber = getCurrentTemporalValue(
    searchParams.get(CURRENT_ROUND_PARAM) || "",
    roundNumbers
  );

  const [predictions, metrics] = await Promise.all([
    fetchRoundPredictions(currentSeasonYear, currentRoundNumber),
    fetchSeasonMetrics(currentSeasonYear),
  ]);
  const roundMetrics = await fetchRoundMetrics(currentSeasonYear);

  return json({
    currentRoundNumber,
    roundNumbers,
    predictions,
    metrics,
    currentSeasonYear,
    seasonYears,
    roundMetrics,
  });
};

export default function Index() {
  const {
    currentRoundNumber,
    roundNumbers,
    predictions,
    metrics,
    seasonYears,
    currentSeasonYear,
    roundMetrics,
  } = useLoaderData<typeof loader>();
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
          {seasonYears && roundNumbers && currentRoundNumber && (
            <Form style={{ padding: "1rem" }}>
              <SeasonSelect
                submit={submit}
                seasonYears={seasonYears}
                currentSeasonYear={currentSeasonYear}
              />
              <RoundSelect
                submit={submit}
                roundNumbers={roundNumbers}
                currentRoundNumber={currentRoundNumber}
              />
            </Form>
          )}
          {currentSeasonYear && (
            <Card marginTop="1rem" marginBottom="1rem" width="100%">
              <CardBody>
                <ResponsiveContainer width="100%" height={600}>
                  <LineChart data={roundMetrics.totalTips}>
                    <CartesianGrid />
                    <XAxis
                      dataKey="roundNumber"
                      label={{
                        value: "Rounds",
                        position: "insideBottom",
                        offset: 25,
                      }}
                      height={70}
                    />
                    <YAxis
                      label={{
                        value: "Total Tips",
                        angle: -90,
                        position: "insideLeft",
                        offset: 15,
                      }}
                    />
                    <Tooltip itemSorter={({ value }) => -(value ?? 0)} />
                    <Legend />
                    {Object.keys(roundMetrics.totalTips[0])
                      .filter((key) => key !== "roundNumber")
                      .sort()
                      .map((mlModelName, idx) => (
                        <Line
                          key={mlModelName}
                          dataKey={mlModelName}
                          stroke={CHART_PALETTE[idx]}
                          fill={CHART_PALETTE[idx]}
                        />
                      ))}
                  </LineChart>
                </ResponsiveContainer>
              </CardBody>
            </Card>
          )}
          {predictions && currentSeasonYear && currentRoundNumber && (
            <Card marginTop="1rem" marginBottom="1rem">
              <CardBody>
                <PredictionsTable
                  currentRound={currentRoundNumber}
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
