import {
  Heading,
  Table,
  TableContainer,
  Tbody,
  Td,
  Th,
  Thead,
  Tr,
} from "@chakra-ui/react";

interface Prediction {
  winner: string;
  loser: string;
  margin: number;
  wasCorrect: boolean | null;
}

interface PredictionsTableProps {
  currentRound: number;
  predictions: Prediction[];
}

export const displayCorrectness = (wasCorrect: boolean | null) => {
  switch (wasCorrect) {
    case true:
      return "yup";
    case false:
      return "nope";
    case null:
      return "dunno";
  }
};

const PredictionRow = ({ winner, loser, margin, wasCorrect }: Prediction) => (
  <Tr key={winner}>
    <Td>{winner}</Td>
    <Td>{loser}</Td>
    <Td isNumeric>{margin}</Td>
    <Td>{displayCorrectness(wasCorrect)}</Td>
  </Tr>
);

const PredictionsTable = ({
  currentRound,
  predictions,
}: PredictionsTableProps) => (
  <TableContainer textAlign="center">
    <Heading as="h2" size="l" margin="0.5rem" whiteSpace="nowrap">
      Predictions for round {currentRound}
    </Heading>
    <Table variant="simple" maxWidth="fit-content">
      <Thead>
        <Tr>
          <Th>Winner</Th>
          <Th>Loser</Th>
          <Th isNumeric>Margin</Th>
          <Th>Correct?</Th>
        </Tr>
      </Thead>
      <Tbody>{predictions.map(PredictionRow)}</Tbody>
    </Table>
  </TableContainer>
);

export default PredictionsTable;
