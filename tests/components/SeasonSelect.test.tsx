import { render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";

import SeasonSelect from "../../app/components/SeasonSelect";

const mockSubmit = jest.fn();
const seasonYears = [2020, 2021, 2022, 2023, 2024];
const currentSeasonYear = 2024;

describe("SeasonSelect", () => {
  it("submits the form on option select", async () => {
    const user = userEvent.setup();

    render(
      <SeasonSelect
        submit={mockSubmit}
        seasonYears={seasonYears}
        currentSeasonYear={currentSeasonYear}
      />
    );

    const select = screen.getByLabelText<HTMLSelectElement>("Season");
    await user.selectOptions(select, "2020");
    expect(mockSubmit).toHaveBeenCalled();
  });
});
