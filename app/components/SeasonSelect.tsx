import { Flex, FormControl, FormLabel, Select } from "@chakra-ui/react";

interface SeasonSelectProps {
  submit: (form: HTMLFormElement | null) => void;
  seasonYears: number[];
  currentSeasonYear: number;
}

interface SeasonOptionProps {
  seasonYear: number;
}

export const CURRENT_SEASON_PARAM = "season";

const SeasonOption = ({ seasonYear }: SeasonOptionProps) => (
  <option value={seasonYear}>{seasonYear}</option>
);

const SeasonSelect = ({
  submit,
  seasonYears,
  currentSeasonYear,
}: SeasonSelectProps) => (
  <FormControl marginLeft="auto" marginRight="auto" maxWidth="15rem">
    <Flex alignItems="center" justifyContent="space-between">
      <FormLabel margin="0.5rem" size="xl">
        Season
      </FormLabel>
      <Select
        name={CURRENT_SEASON_PARAM}
        defaultValue={currentSeasonYear}
        onChange={(event) => submit(event.currentTarget.form)}
        maxWidth="60%"
      >
        {seasonYears.map((seasonYear) => (
          <SeasonOption seasonYear={seasonYear} key={seasonYear} />
        ))}
      </Select>
    </Flex>
  </FormControl>
);

export default SeasonSelect;
