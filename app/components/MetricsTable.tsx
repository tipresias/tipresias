import {
  Heading,
  Table,
  TableContainer,
  Tbody,
  Td,
  Th,
  Tr,
} from "@chakra-ui/react";

interface Metric {
  name: string;
  value: string;
}

interface MetricsTableProps {
  metrics: Metric[];
  season: number;
}

const MetricRow = ({ name, value }: Metric) => (
  <Tr key={name}>
    <Th>{name}</Th>
    <Td isNumeric>{value}</Td>
  </Tr>
);

const MetricsTable = ({ metrics, season }: MetricsTableProps) => (
  <TableContainer textAlign="center">
    <Heading as="h2" size="l" margin="0.5rem" whiteSpace="nowrap">
      Model performance for {season}
    </Heading>
    <Table variant="simple" maxWidth="fit-content">
      <Tbody>{metrics.map(MetricRow)}</Tbody>
    </Table>
  </TableContainer>
);

export default MetricsTable;
