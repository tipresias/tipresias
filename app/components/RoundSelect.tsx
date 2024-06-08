import { Flex, FormControl, FormLabel, Select } from "@chakra-ui/react";

interface RoundSelectProps {
  submit: (form: HTMLFormElement | null) => void;
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
  submit,
  roundNumbers,
  currentRoundNumber,
}: RoundSelectProps) => (
  <FormControl margin="0.5rem">
    <Flex alignItems="center" justifyContent="space-between">
      <FormLabel margin="0.5rem" size="xl">
        Round
      </FormLabel>
      <Select
        name={CURRENT_ROUND_PARAM}
        value={currentRoundNumber}
        onChange={(event) => submit(event.currentTarget.form)}
        maxWidth="60%"
      >
        {roundNumbers.map((roundNumber) => (
          <RoundOption roundNumber={roundNumber} key={roundNumber} />
        ))}
      </Select>
    </Flex>
  </FormControl>
);

export default RoundSelect;
