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
import { Flex, FormControl, FormLabel, Select } from "@chakra-ui/react";
import { useState } from "react";

import {
  MlModelRoundMetrics,
  RoundMetrics,
} from "../.server/predictionService";

interface MetricsChartProps {
  roundMetrics: RoundMetrics;
}
type MetricName = keyof RoundMetrics;
interface MetricSelectProps {
  roundMetrics: RoundMetrics;
  currentMetric: MetricName;
  setCurrentMetric: (metric: MetricName) => void;
}

const CHART_PALETTE = [
  "#E69F00",
  "#56B4E9",
  "#CC79A7",
  "#009E73",
  "#0072B2",
  "#D55E00",
  "#F0E442",
];
const METRIC_LABELS = {
  totalTips: "Total Tips",
  accuracy: "Accuracy",
  mae: "MAE",
  bits: "Bits",
};

const isMetricName = (maybeMetricName: string): maybeMetricName is MetricName =>
  Object.keys(METRIC_LABELS).includes(maybeMetricName);

const getModelNames = (mlModelRoundMetrics: MlModelRoundMetrics[]) =>
  Object.keys(mlModelRoundMetrics[0])
    .filter((key) => key !== "roundNumber")
    .sort();

const MetricSelect = ({
  roundMetrics,
  currentMetric,
  setCurrentMetric,
}: MetricSelectProps) => (
  <FormControl
    margin="0.5rem"
    maxWidth="30%"
    marginLeft="auto"
    marginRight="auto"
  >
    <Flex alignItems="center" justifyContent="space-between">
      <FormLabel margin="0.5rem" size="xl">
        Metric
      </FormLabel>
      <Select
        name={"metric"}
        value={currentMetric}
        onChange={(event) => {
          const metricName = event.currentTarget.value;
          if (isMetricName(metricName)) setCurrentMetric(metricName);
        }}
      >
        {Object.entries(roundMetrics)
          .filter(([_, metricValues]) => getModelNames(metricValues).length)
          .map(([metric]) => (
            <option value={metric} key={metric}>
              {METRIC_LABELS[metric as MetricName]}
            </option>
          ))}
      </Select>
    </Flex>
  </FormControl>
);

const MetricsChart = ({ roundMetrics }: MetricsChartProps) => {
  const [currentMetric, setCurrentMetric] = useState<MetricName>("totalTips");

  return (
    <>
      <MetricSelect
        roundMetrics={roundMetrics}
        currentMetric={currentMetric}
        setCurrentMetric={setCurrentMetric}
      />
      <ResponsiveContainer width="100%" height={600}>
        <LineChart data={roundMetrics[currentMetric]}>
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
              value: METRIC_LABELS[currentMetric],
              angle: -90,
              position: "insideLeft",
              offset: 15,
            }}
          />
          <Tooltip itemSorter={({ value }) => -(value ?? 0)} />
          <Legend />
          {getModelNames(roundMetrics[currentMetric]).map(
            (mlModelName, idx) => (
              <Line
                key={mlModelName}
                dataKey={mlModelName}
                stroke={CHART_PALETTE[idx]}
                fill={CHART_PALETTE[idx]}
              />
            )
          )}
        </LineChart>
      </ResponsiveContainer>
    </>
  );
};

export default MetricsChart;
