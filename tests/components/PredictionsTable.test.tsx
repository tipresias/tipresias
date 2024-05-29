import { faker } from "@faker-js/faker";
import { render, screen } from "@testing-library/react";
import round from "lodash/round";

import PredictionsTable, {
  displayCorrectness,
} from "../../app/components/PredictionsTable";

describe("PredictionsTable", () => {
  const currentRound = faker.number.int();
  const predictions = new Array(9).fill(null).map(() => ({
    predictedWinnerName: faker.company.name(),
    predictedMargin: faker.number.float(),
    predictedWinProbability: faker.number.float(),
    isCorrect:
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

    const {
      predictedWinnerName,
      predictedMargin,
      predictedWinProbability,
      isCorrect,
    } = faker.helpers.arrayElement(predictions);

    screen.getByText(predictedWinnerName);
    screen.getByText(String(round(predictedMargin, 2)));
    screen.getByText(String(round(predictedWinProbability, 2)));
    screen.getAllByText(displayCorrectness(isCorrect));
  });
});
