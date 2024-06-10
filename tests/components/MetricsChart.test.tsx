import { render, screen } from "@testing-library/react";
import MetricsChart from "../../app/components/MetricsChart";
import { faker } from "@faker-js/faker";
import { userEvent } from "@testing-library/user-event";

// ResponsiveContainer uses ResizeObeserver under the hood,
// so we need to mock it in order to avoid errors.
window.ResizeObserver =
  window.ResizeObserver ||
  jest.fn().mockImplementation(() => ({
    disconnect: jest.fn(),
    observe: jest.fn(),
    unobserve: jest.fn(),
  }));

describe("MetricsChart", () => {
  const fakeRoundMetrics = [
    {
      roundNumber: faker.number.int(),
      modelA: faker.number.float(),
      modelB: faker.number.float(),
    },
  ];
  const mockLoadData = jest.fn();
  const fakeSeasonYear = 2020;

  it("selects a different metric", async () => {
    const user = userEvent.setup();
    render(
      <MetricsChart
        roundMetrics={fakeRoundMetrics}
        loadData={mockLoadData}
        seasonYear={fakeSeasonYear}
      />
    );
    const select = screen.getByLabelText<HTMLSelectElement>("Metric");
    await user.selectOptions(select, "Accuracy");
    expect(mockLoadData).toHaveBeenCalled();
    expect(select.value).toEqual("accuracy");
  });
});
