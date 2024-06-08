import { render, screen } from "@testing-library/react";
import { userEvent } from "@testing-library/user-event";

import RoundSelect from "../../app/components/RoundSelect";

const mockSubmit = jest.fn();
const roundNumbers = [1, 2, 3, 4, 5];
const currentRoundNumber = 5;

describe("SeasonSelect", () => {
  it("submits the form on option select", async () => {
    const user = userEvent.setup();

    render(
      <RoundSelect
        submit={mockSubmit}
        roundNumbers={roundNumbers}
        currentRoundNumber={currentRoundNumber}
      />
    );

    const select = screen.getByLabelText<HTMLSelectElement>("Round");
    await user.selectOptions(select, "1");
    expect(mockSubmit).toHaveBeenCalled();
  });
});
