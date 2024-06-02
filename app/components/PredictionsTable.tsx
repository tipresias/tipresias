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
import round from "lodash/round";

import { Prediction } from "~/.server/predictionService";

interface PredictionsTableProps {
  currentRound: number;
  currentSeason: number;
  predictions: Prediction[];
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
}: Prediction) => (
  <Tr key={predictedWinnerName}>
    <Td>{predictedWinnerName}</Td>
    <Td isNumeric>{round(predictedMargin || NaN, 2) || "NA"}</Td>
    <Td isNumeric>{round(predictedWinProbability || NaN, 2) || "NA"}</Td>
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
