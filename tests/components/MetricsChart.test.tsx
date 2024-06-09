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
  const fakeRoundModelMetrics = [
    {
      roundNumber: faker.number.int(),
      modelA: faker.number.float(),
      modelB: faker.number.float(),
    },
  ];
  const fakeRoundMetrics = {
    totalTips: fakeRoundModelMetrics,
    accuracy: fakeRoundModelMetrics,
    mae: fakeRoundModelMetrics,
    bits: fakeRoundModelMetrics,
  };

  it("renders the chart", async () => {
    const user = userEvent.setup();
    render(<MetricsChart roundMetrics={fakeRoundMetrics} />);
    const select = screen.getByLabelText<HTMLSelectElement>("Metric");
    await user.selectOptions(select, "Accuracy");
    expect(select.value).toEqual("accuracy");
  });
});
