import {
  Heading,
  Table,
  TableContainer,
  Tbody,
  Td,
  Th,
  Tr,
} from "@chakra-ui/react";

import { Metrics } from "../.server/predictionService";
import { presentNumber } from "../helpers/number";

interface Metric {
  name: keyof Metrics;
  value: number | null;
}

interface MetricsTableProps {
  metrics: Metrics;
  season: number;
}

const ROW_ORDER: Array<keyof Metrics> = [
  "totalTips",
  "accuracy",
  "mae",
  "bits",
];
export const METRIC_LABEL_MAP: Record<keyof Metrics, string> = {
  totalTips: "Total Tips",
  accuracy: "Accuracy",
  mae: "MAE",
  bits: "Bits",
};

const MetricRow = ({ name, value }: Metric) => (
  <Tr>
    <Th>{METRIC_LABEL_MAP[name]}</Th>
    <Td isNumeric>{presentNumber(value)}</Td>
  </Tr>
);

const MetricsTable = ({ metrics, season }: MetricsTableProps) => (
  <TableContainer textAlign="center">
    <Heading as="h2" size="l" margin="0.5rem" whiteSpace="nowrap">
      Model performance for {season}
    </Heading>
    <Table variant="simple">
      <Tbody>
        {ROW_ORDER.map((metricKey) => (
          <MetricRow
            key={metricKey}
            name={metricKey}
            value={metrics[metricKey]}
          />
        ))}
      </Tbody>
    </Table>
  </TableContainer>
);

export default MetricsTable;
