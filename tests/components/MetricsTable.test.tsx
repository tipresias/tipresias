import { faker } from "@faker-js/faker";
import { render, screen } from "@testing-library/react";

import MetricsTable from "../../app/components/MetricsTable";

describe("MetricsTable", () => {
  const metrics = new Array(4).fill(null).map((_, idx) => ({
    name: `${faker.company.buzzNoun()}${idx}`,
    value: faker.number.float().toString(),
  }));
  const season = faker.number.int();

  it("displays the table title", () => {
    render(<MetricsTable metrics={metrics} season={season} />);

    screen.getByText(`Model performance for ${season}`);
  });

  it("displays metrics", () => {
    render(<MetricsTable metrics={metrics} season={season} />);

    const { name, value } = faker.helpers.arrayElement(metrics);

    screen.getByText(name);
    screen.getByText(value);
  });
});
