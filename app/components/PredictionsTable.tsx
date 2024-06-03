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

import { RoundPrediction } from "../.server/predictionService";
import { presentNumber } from "../helpers/number";

interface PredictionsTableProps {
  currentRound: number;
  currentSeason: number;
  predictions: RoundPrediction[];
}

export const displayCorrectness = (wasCorrect: boolean | null) => {
  switch (wasCorrect) {
    case true:
      return "yeah";
    case false:
      return "nah";
    case null:
      return "dunno";
  }
};

const PredictionRow = ({
  predictedWinnerName,
  predictedMargin,
  predictedWinProbability,
  isCorrect,
}: RoundPrediction) => (
  <Tr key={predictedWinnerName}>
    <Td>{predictedWinnerName}</Td>
    <Td isNumeric>{presentNumber(predictedMargin)}</Td>
    <Td isNumeric>{presentNumber(predictedWinProbability)}</Td>
    <Td>{displayCorrectness(isCorrect)}</Td>
  </Tr>
);

const PredictionsTable = ({
  currentRound,
  currentSeason,
  predictions,
}: PredictionsTableProps) => (
  <TableContainer textAlign="center">
    <Heading as="h2" size="l" margin="0.5rem" whiteSpace="nowrap">
      Predictions for round {currentRound}, {currentSeason}
    </Heading>
    <Table variant="striped" maxWidth="fit-content">
      <Thead>
        <Tr>
          <Th>Predicted Winner</Th>
          <Th isNumeric>Predicted Margin</Th>
          <Th isNumeric>Predicted Win Probability (%)</Th>
          <Th>Correct?</Th>
        </Tr>
      </Thead>
      <Tbody>{predictions.map(PredictionRow)}</Tbody>
    </Table>
  </TableContainer>
);

export default PredictionsTable;
