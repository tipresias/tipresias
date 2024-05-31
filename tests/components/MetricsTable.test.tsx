import { faker } from "@faker-js/faker";
import { render, screen } from "@testing-library/react";
import round from "lodash/round";

import MetricsTable, {
  METRIC_LABEL_MAP,
  Metrics,
} from "../../app/components/MetricsTable";

describe("MetricsTable", () => {
  const metrics = {
    totalTips: faker.number.float(),
    accuracy: faker.number.float(),
    mae: faker.number.float(),
    bits: faker.number.float(),
  };
  const season = faker.number.int();

  it("displays the table title", () => {
    render(<MetricsTable metrics={metrics} season={season} />);

    screen.getByText(`Model performance for ${season}`);
  });

  it("displays metrics", () => {
    render(<MetricsTable metrics={metrics} season={season} />);

    Object.entries(metrics).forEach(([name, value]) => {
      screen.getByText(METRIC_LABEL_MAP[name as keyof Metrics]);
      screen.getByText(round(value, 2));
    });
  });
});
