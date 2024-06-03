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
import { presentNumber, presentPercentage } from "../helpers/number";

interface MetricsTableProps {
  metrics: Metrics;
  season: number;
}

const MetricRow = ({ name, value }: { name: string; value: string }) => (
  <Tr>
    <Th>{name}</Th>
    <Td isNumeric>{value}</Td>
  </Tr>
);

const MetricsTable = ({ metrics, season }: MetricsTableProps) => (
  <TableContainer textAlign="center">
    <Heading as="h2" size="l" margin="0.5rem" whiteSpace="nowrap">
      Model performance for {season}
    </Heading>
    <Table variant="simple">
      <Tbody>
        <MetricRow
          name={"Total Tips"}
          value={presentNumber(metrics.totalTips)}
        />
        <MetricRow
          name={"Accuracy"}
          value={presentPercentage(metrics.accuracy)}
        />
        <MetricRow name={"MAE"} value={presentNumber(metrics.mae, 2)} />
        <MetricRow name={"Bits"} value={presentNumber(metrics.bits, 2)} />
      </Tbody>
    </Table>
  </TableContainer>
);

export default MetricsTable;
