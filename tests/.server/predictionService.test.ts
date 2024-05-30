/**
 * @jest-environment node
 */
import { faker } from "@faker-js/faker";
import { fetchRoundPredictions } from "../../app/.server/predictionService";

jest.mock("../../app/.server/db", () => {
  return {
    sqlQuery: jest.fn(async () =>
      new Array(9).fill(null).map(() => ({
        predictedWinnerName: faker.company.name(),
        predictedMargin: faker.number.float(),
        predictedWinProbability: faker.number.float(),
        isCorrect:
          faker.helpers.maybe(faker.datatype.boolean, {
            probability: faker.number.float(),
          }) ?? null,
      }))
    ),
  };
});

describe("fetchRoundPredictions", () => {
  it("fetches prediction records from the DB", async () => {
    const predictions = await fetchRoundPredictions();
    expect(predictions.length).toEqual(9);
  });

  it("converts record keys to camelCase", async () => {
    const predictions = await fetchRoundPredictions();
    const predictionKeys = new Set(predictions.flatMap(Object.keys));
    const expectedPredictionKeys = new Set([
      "predictedWinnerName",
      "predictedMargin",
      "predictedWinProbability",
      "isCorrect",
    ]);
    expect(predictionKeys).toEqual(expectedPredictionKeys);
  });
});
