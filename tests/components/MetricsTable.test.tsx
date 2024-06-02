import { faker } from "@faker-js/faker";
import { render, screen } from "@testing-library/react";
import round from "lodash/round";

import MetricsTable, {
  METRIC_LABEL_MAP,
} from "../../app/components/MetricsTable";
import { Metrics } from "../../app/.server/predictionService";

describe("MetricsTable", () => {
  const season = faker.number.int();

  describe("when all values are present", () => {
    const metrics = {
      totalTips: faker.number.float(),
      accuracy: faker.number.float(),
      mae: faker.number.float(),
      bits: faker.number.float(),
    };

    it("displays the table title", () => {
      render(<MetricsTable metrics={metrics} season={season} />);

      screen.getByText(`Model performance for ${season}`);
    });

    it("displays metrics", () => {
      render(<MetricsTable metrics={metrics} season={season} />);

      Object.entries(metrics).forEach(([name, value]) => {
        screen.getByText(METRIC_LABEL_MAP[name as keyof Metrics]);
        screen.getAllByText(round(value, 2));
      });
    });
  });

  describe("when some values are null", () => {
    const metrics = {
      totalTips: null,
      accuracy: null,
      mae: null,
      bits: null,
    };

    it("displays NA for missing values", () => {
      render(<MetricsTable metrics={metrics} season={season} />);

      const naElements = screen.getAllByText("NA");
      expect(naElements).toHaveLength(4);
    });
  });
});
