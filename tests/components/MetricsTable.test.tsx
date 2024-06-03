import { faker } from "@faker-js/faker";
import { render, screen } from "@testing-library/react";

import MetricsTable from "../../app/components/MetricsTable";

describe("MetricsTable", () => {
  const season = faker.number.int();

  describe("when all values are present", () => {
    const metrics = {
      totalTips: faker.number.int(),
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

      screen.getByText("Total Tips");
      screen.getAllByText(metrics.totalTips.toString());
      screen.getByText("Accuracy");
      screen.getAllByText(`${(metrics.accuracy * 100).toFixed(2)}%`);
      screen.getByText("MAE");
      screen.getAllByText(metrics.mae.toFixed(2));
      screen.getByText("Bits");
      screen.getAllByText(metrics.bits.toFixed(2));
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
