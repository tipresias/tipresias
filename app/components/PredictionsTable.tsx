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
import { InfoOutlineIcon } from "@chakra-ui/icons";
import { useCallback, useEffect, useState } from "react";
import max from "lodash/max";

import RoundSelect from "./RoundSelect";
import { RoundPrediction } from "../.server/predictionService";
import { presentNumber, presentPercentage } from "../helpers/number";

interface PredictionsTableProps {
  predictions: RoundPrediction[];
  roundNumbers: number[];
  seasonYear: number;
  loadData: (href: string) => void;
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
  loadData,
  predictions,
  seasonYear,
  roundNumbers,
}: PredictionsTableProps) => {
  const [roundNumber, setRoundNumber] = useState<number | undefined>(
    max(roundNumbers)
  );

  const loadPredictions = useCallback(
    (newRoundNumber: number) => {
      loadData(`seasons/${seasonYear}/rounds/${newRoundNumber}/predictions`);
      setRoundNumber(newRoundNumber);
    },
    [seasonYear]
  );

  useEffect(() => {
    const newRoundNumber = max(roundNumbers);
    if (!newRoundNumber) return;
    setRoundNumber(newRoundNumber);
    loadPredictions(newRoundNumber);
  }, [roundNumbers]);

  if (roundNumber === undefined) return null;

  return (
    <>
      <RoundSelect
        loadPredictions={loadPredictions}
        roundNumbers={roundNumbers}
        currentRoundNumber={roundNumber}
      />
      <TableContainer textAlign="center">
        <Heading as="h2" size="l" margin="0.5rem" whiteSpace="nowrap">
          Predictions for Round {roundNumber}, {seasonYear}{" "}
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
    </>
  );
};

export default PredictionsTable;
