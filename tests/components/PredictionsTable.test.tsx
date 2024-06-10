import { faker } from "@faker-js/faker";
import { render, screen } from "@testing-library/react";

import PredictionsTable, {
  displayCorrectness,
} from "../../app/components/PredictionsTable";

describe("PredictionsTable", () => {
  const seasonYear = faker.number.int();
  const roundNumbers = new Array(12).fill(null).map((_, idx) => idx + 1);
  const fakeLoadData = jest.fn();

  describe("when all values are present", () => {
    const predictions = new Array(9).fill(null).map(() => ({
      predictedWinnerName: faker.company.name(),
      predictedMargin: faker.number.float(),
      predictedWinProbability: faker.number.float(),
      isCorrect:
        faker.helpers.maybe(faker.datatype.boolean, { probability: 0.67 }) ??
        null,
    }));

    it("displays the table title with year and max round", () => {
      render(
        <PredictionsTable
          loadData={fakeLoadData}
          predictions={predictions}
          seasonYear={seasonYear}
          roundNumbers={roundNumbers}
        />
      );

      screen.getByText(
        `Predictions for Round ${
          roundNumbers[roundNumbers.length - 1]
        }, ${seasonYear}`
      );
    });

    it("displays predictions", () => {
      render(
        <PredictionsTable
          loadData={fakeLoadData}
          predictions={predictions}
          seasonYear={seasonYear}
          roundNumbers={roundNumbers}
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
      screen.getAllByText(`${(predictedWinProbability * 100).toFixed(2)}%`);
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
          loadData={fakeLoadData}
          predictions={predictions}
          seasonYear={seasonYear}
          roundNumbers={roundNumbers}
        />
      );

      const naElements = screen.getAllByText("NA");
      expect(naElements).toHaveLength(2);
    });
  });
});
