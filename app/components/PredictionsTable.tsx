import {
  Heading,
  Table,
  TableContainer,
  Tbody,
  Td,
  Th,
  Thead,
  Tooltip,
  Tr,
} from "@chakra-ui/react";

import { RoundPrediction } from "../.server/predictionService";
import { presentNumber, presentPercentage } from "../helpers/number";
import { InfoOutlineIcon } from "@chakra-ui/icons";

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

const PREDICTION_INFO = `Margin and win probability are generated
  by different models that sometimes disagree. In those cases,
  the secondary prediction will be for a loss for the given team,
  resulting in negative margins or win probabilities of less than 0.5.`;
const PredictionInfoTooltip = () => (
  <Tooltip
    label={PREDICTION_INFO}
    aria-label="Prediction info tooltip"
    placement="top-start"
  >
    <InfoOutlineIcon />
  </Tooltip>
);

const PredictionRow = ({
  predictedWinnerName,
  predictedMargin,
  predictedWinProbability,
  isCorrect,
}: RoundPrediction) => (
  <Tr key={predictedWinnerName}>
    <Td>{predictedWinnerName}</Td>
    <Td isNumeric>{presentNumber(predictedMargin, 2)}</Td>
    <Td isNumeric>{presentPercentage(predictedWinProbability)}</Td>
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
      Predictions for round {currentRound}, {currentSeason}{" "}
      <PredictionInfoTooltip />
    </Heading>
    <Table variant="striped" maxWidth="fit-content">
      <Thead>
        <Tr>
          <Th>Predicted Winner</Th>
          <Th isNumeric>Predicted Margin</Th>
          <Th isNumeric>Predicted Win Probability</Th>
          <Th>Correct?</Th>
        </Tr>
      </Thead>
      <Tbody>{predictions.map(PredictionRow)}</Tbody>
    </Table>
  </TableContainer>
);

export default PredictionsTable;
