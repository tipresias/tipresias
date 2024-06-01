/**
 * @jest-environment node
 */
import { faker } from "@faker-js/faker";
import {
  Metrics,
  MetricsRecord,
  RoundPredictionRecord,
  fetchRoundMetrics,
  fetchRoundPredictions,
} from "../../app/.server/predictionService";
import * as db from "../../app/.server/db";

const mockSqlQuery = jest.spyOn(db, "sqlQuery");

describe("fetchRoundPredictions", () => {
  beforeAll(() => {
    const fakePredictions = new Array(9).fill(null).map(() => ({
      predicted_winner_name: faker.company.name(),
      predicted_margin: faker.number.float(),
      predicted_win_probability: faker.number.float(),
      is_correct:
        faker.helpers.maybe(faker.datatype.boolean, {
          probability: faker.number.float(),
        }) ?? null,
    }));
    const mockSqlQueryImplementation = (async () =>
      fakePredictions) as typeof db.sqlQuery<RoundPredictionRecord[]>;
    mockSqlQuery.mockImplementation(mockSqlQueryImplementation);
  });

  it("fetches predictions from the DB", async () => {
    const predictions = await fetchRoundPredictions();
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

describe("fetchRoundMetrics", () => {
  describe("when prediction are available", () => {
    beforeAll(() => {
      const fakeMetrics = [
        {
          total_tips: faker.number.int(),
          accuracy: faker.number.float(),
          mae: faker.number.float(),
          bits: faker.number.float(),
        },
      ];
      const mockSqlQueryImplementation = (async () =>
        fakeMetrics) as typeof db.sqlQuery<MetricsRecord[]>;
      mockSqlQuery.mockImplementation(mockSqlQueryImplementation);
    });

    it("returns a metrics object", async () => {
      const metrics = await fetchRoundMetrics();
      expect(metrics).toMatchObject<Metrics>({
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
          total_tips: null,
          accuracy: null,
          mae: null,
          bits: null,
        },
      ];
      const mockSqlQueryImplementation = (async () =>
        fakeMetrics) as typeof db.sqlQuery<MetricsRecord[]>;
      mockSqlQuery.mockImplementation(mockSqlQueryImplementation);
    });

    it("returns a blank metrics object", async () => {
      const metrics = await fetchRoundMetrics();
      expect(metrics).toMatchObject<Metrics>({
        totalTips: null,
        accuracy: null,
        mae: null,
        bits: null,
      });
    });
  });
});
