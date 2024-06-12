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
import { ChangeEvent, useCallback, useEffect, useState } from "react";

import { RoundMetrics, MetricName } from "../.server/predictionService";
import { presentNumber, presentPercentage } from "../helpers/number";

interface MetricsChartProps {
  roundMetrics: RoundMetrics[];
  seasonYear: number;
  loadData: (href: string) => void;
}
interface MetricSelectProps {
  loadMetrics: (metricName: MetricName) => void;
  currentMetric: MetricName;
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
const METRIC_LABELS: Record<MetricName, string> = {
  totalTips: "Total Tips",
  accuracy: "Accuracy",
  mae: "MAE",
  bits: "Bits",
};
const METRIC_PRESENTERS: Record<
  MetricName,
  (value: number | null, fractionDigits: number | undefined) => string
> = {
  totalTips: (value) => presentNumber(value),
  accuracy: presentPercentage,
  mae: presentNumber,
  bits: presentNumber,
};

const isMetricName = (maybeMetricName: string): maybeMetricName is MetricName =>
  Object.keys(METRIC_LABELS).includes(maybeMetricName);

const getModelNames = (roundMetrics: RoundMetrics[]) =>
  Object.keys(roundMetrics[0] || {})
    .filter((key) => key !== "roundNumber")
    .sort();

const MetricSelect = ({ currentMetric, loadMetrics }: MetricSelectProps) => {
  const onMetricChange = (event: ChangeEvent<HTMLSelectElement>) => {
    const metricName = event.currentTarget.value;
    if (isMetricName(metricName)) loadMetrics(metricName);
  };

  return (
    <FormControl
      margin="0.5rem"
      maxWidth="15rem"
      marginLeft="auto"
      marginRight="auto"
    >
      <Flex alignItems="center" justifyContent="space-between">
        <FormLabel margin="0.5rem" marginRight="2.5rem" size="xl">
          Metric
        </FormLabel>
        <Select name={"metric"} value={currentMetric} onChange={onMetricChange}>
          {Object.entries(METRIC_LABELS).map(([metricName, metricLabel]) => (
            <option value={metricName} key={metricName}>
              {metricLabel}
            </option>
          ))}
        </Select>
      </Flex>
    </FormControl>
  );
};

const MetricsChart = ({
  roundMetrics,
  loadData,
  seasonYear,
}: MetricsChartProps) => {
  const [metricName, setMetricName] = useState<MetricName>("totalTips");

  const loadMetrics = useCallback(
    (newMetricName: MetricName) => {
      loadData(`seasons/${seasonYear}/metrics/${newMetricName}`);
      setMetricName(newMetricName);
    },
    [loadData, setMetricName, seasonYear]
  );

  useEffect(() => {
    loadMetrics(metricName);
  }, [metricName, loadMetrics]);

  const yAxisOffset = metricName === "accuracy" ? 5 : 15;

  return (
    <>
      <MetricSelect loadMetrics={loadMetrics} currentMetric={metricName} />
      <ResponsiveContainer width="100%" height={600}>
        <LineChart data={roundMetrics}>
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
              value: METRIC_LABELS[metricName],
              angle: -90,
              position: "insideLeft",
              offset: yAxisOffset,
            }}
            tickFormatter={(value: number) =>
              METRIC_PRESENTERS[metricName](value, 0)
            }
          />
          <Tooltip
            itemSorter={({ value }) => -(value ?? 0)}
            formatter={(value) =>
              METRIC_PRESENTERS[metricName](value as number, 2)
            }
          />
          <Legend />
          {getModelNames(roundMetrics).map((mlModelName, idx) => (
            <Line
              key={mlModelName}
              dataKey={mlModelName}
              stroke={CHART_PALETTE[idx]}
              fill={CHART_PALETTE[idx]}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </>
  );
};

export default MetricsChart;
