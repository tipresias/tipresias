import { Flex, FormControl, FormLabel, Select } from "@chakra-ui/react";
import { ChangeEvent } from "react";

interface RoundSelectProps {
  loadPredictions: (roundNumber: number) => void;
  roundNumbers: number[];
  currentRoundNumber: number;
}

interface RoundOptionProps {
  roundNumber: number;
}

export const CURRENT_ROUND_PARAM = "round";

const RoundOption = ({ roundNumber }: RoundOptionProps) => (
  <option value={roundNumber}>{roundNumber}</option>
);

const RoundSelect = ({
  loadPredictions,
  roundNumbers,
  currentRoundNumber,
}: RoundSelectProps) => {
  const onRoundChange = (event: ChangeEvent<HTMLSelectElement>) => {
    const roundNumber = parseInt(event.currentTarget.value);
    loadPredictions(roundNumber);
  };

  return (
    <FormControl margin="0.5rem">
      <Flex alignItems="center" justifyContent="center">
        <FormLabel margin="0.5rem" size="xl">
          Round
        </FormLabel>
        <Select
          name={CURRENT_ROUND_PARAM}
          value={currentRoundNumber}
          onChange={onRoundChange}
          maxWidth="5rem"
        >
          {roundNumbers.map((roundNumber) => (
            <RoundOption roundNumber={roundNumber} key={roundNumber} />
          ))}
        </Select>
      </Flex>
    </FormControl>
  );
};

export default RoundSelect;
