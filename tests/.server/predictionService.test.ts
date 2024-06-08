/**
 * @jest-environment node
 */
import { faker } from "@faker-js/faker";
import {
  SeasonMetrics,
  RoundPrediction,
  fetchSeasonMetrics,
  fetchRoundPredictions,
} from "../../app/.server/predictionService";
import * as db from "../../app/.server/db";

const mockSqlQuery = jest.spyOn(db, "sqlQuery");

describe("fetchRoundPredictions", () => {
  const seasonYear = 2020;
  const roundNumber = 5;

  beforeAll(() => {
    const fakePredictions = new Array(9).fill(null).map(() => ({
      predictedWinnerName: faker.company.name(),
      predictedMargin: faker.number.float(),
      predictedWinProbability: faker.number.float(),
      isCorrect:
        faker.helpers.maybe(faker.datatype.boolean, {
          probability: faker.number.float(),
        }) ?? null,
    }));
    const mockSqlQueryImplementation = (async () =>
      fakePredictions) as typeof db.sqlQuery<RoundPrediction[]>;
    mockSqlQuery.mockImplementation(mockSqlQueryImplementation);
  });

  it("fetches predictions from the DB", async () => {
    const predictions = await fetchRoundPredictions(seasonYear, roundNumber);
    expect(predictions).toHaveLength(9);
    predictions.forEach((prediction) => {
      expect(prediction).toMatchObject({
        predictedWinnerName: expect.any(String),
        predictedMargin: expect.any(Number),
        predictedWinProbability: expect.any(Number),
      });
      expect([true, false, null]).toContain(prediction.isCorrect);
    });
  });
});

describe("fetchSeasonMetrics", () => {
  const seasonYear = 2020;

  describe("when prediction are available", () => {
    beforeAll(() => {
      const fakeMetrics = [
        {
          totalTips: faker.number.int(),
          accuracy: faker.number.float(),
          mae: faker.number.float(),
          bits: faker.number.float(),
        },
      ];
      const mockSqlQueryImplementation = (async () =>
        fakeMetrics) as typeof db.sqlQuery<SeasonMetrics[]>;
      mockSqlQuery.mockImplementation(mockSqlQueryImplementation);
    });

    it("returns a metrics object", async () => {
      const metrics = await fetchSeasonMetrics(2020);
      expect(metrics).toMatchObject<SeasonMetrics>({
        totalTips: expect.any(Number),
        accuracy: expect.any(Number),
        mae: expect.any(Number),
        bits: expect.any(Number),
      });
    });
  });

  describe("when no predictions are available", () => {
    beforeAll(() => {
      const fakeMetrics = [
        {
          totalTips: null,
          accuracy: null,
          mae: null,
          bits: null,
        },
      ];
      const mockSqlQueryImplementation = (async () =>
        fakeMetrics) as typeof db.sqlQuery<SeasonMetrics[]>;
      mockSqlQuery.mockImplementation(mockSqlQueryImplementation);
    });

    it("returns a blank metrics object", async () => {
      const metrics = await fetchSeasonMetrics(seasonYear);
      expect(metrics).toMatchObject<SeasonMetrics>({
        totalTips: null,
        accuracy: null,
        mae: null,
        bits: null,
      });
    });
  });
});
