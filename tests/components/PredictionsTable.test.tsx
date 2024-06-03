import { faker } from "@faker-js/faker";
import { render, screen } from "@testing-library/react";

import PredictionsTable, {
  displayCorrectness,
} from "../../app/components/PredictionsTable";

describe("PredictionsTable", () => {
  const currentRound = faker.number.int();
  const currentSeason = faker.number.int();

  describe("when all values are present", () => {
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
        <PredictionsTable
          currentRound={currentRound}
          currentSeason={currentSeason}
          predictions={predictions}
        />
      );

      screen.getByText(
        `Predictions for round ${currentRound}, ${currentSeason}`
      );
    });

    it("displays predictions", () => {
      render(
        <PredictionsTable
          currentRound={currentRound}
          currentSeason={currentSeason}
          predictions={predictions}
        />
      );

      const {
        predictedWinnerName,
        predictedMargin,
        predictedWinProbability,
        isCorrect,
      } = faker.helpers.arrayElement(predictions);

      screen.getByText(predictedWinnerName);
      screen.getAllByText(predictedMargin.toFixed(2));
      screen.getAllByText(predictedWinProbability.toFixed(2));
      screen.getAllByText(displayCorrectness(isCorrect));
    });
  });

  describe("when some values are null", () => {
    const predictions = [
      {
        predictedWinnerName: faker.company.name(),
        predictedMargin: null,
        predictedWinProbability: null,
        isCorrect:
          faker.helpers.maybe(faker.datatype.boolean, { probability: 0.67 }) ??
          null,
      },
    ];

    it("displays NA for missing values", () => {
      render(
        <PredictionsTable
          currentRound={currentRound}
          currentSeason={currentSeason}
          predictions={predictions}
        />
      );

      const naElements = screen.getAllByText("NA");
      expect(naElements).toHaveLength(2);
    });
  });
});
