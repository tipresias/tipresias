import { faker } from "@faker-js/faker";
import { render, screen } from "@testing-library/react";

import PredictionsTable, {
  displayCorrectness,
} from "../../app/components/PredictionsTable";

describe("PredictionsTable", () => {
  const currentRound = faker.number.int();
  const predictions = new Array(9).fill(null).map(() => ({
    winner: faker.company.name(),
    loser: faker.company.name(),
    margin: faker.number.float(),
    wasCorrect:
      faker.helpers.maybe(faker.datatype.boolean, { probability: 0.67 }) ??
      null,
  }));

  it("displays the table title", () => {
    render(
      <PredictionsTable currentRound={currentRound} predictions={predictions} />
    );

    screen.getByText(`Predictions for round ${currentRound}`);
  });

  it("displays predictions", () => {
    render(
      <PredictionsTable currentRound={currentRound} predictions={predictions} />
    );

    const { winner, loser, margin, wasCorrect } =
      faker.helpers.arrayElement(predictions);

    screen.getByText(winner);
    screen.getByText(loser);
    screen.getByText(String(margin));
    screen.getAllByText(displayCorrectness(wasCorrect));
  });
});
