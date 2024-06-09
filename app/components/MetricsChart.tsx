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
import { RoundMetrics } from "../.server/predictionService";

interface MetricsChartProps {
  roundMetrics: RoundMetrics;
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

const MetricsChart = ({ roundMetrics }: MetricsChartProps) => (
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
);

export default MetricsChart;
