/**
 * @jest-environment node
 */

import {
  Round,
  fetchPredictedRoundNumbers,
  fetchSeasons,
} from "../../app/.server/seasonService";
import * as db from "../../app/.server/db";

const fakeSeasons = Array(5)
  .fill(null)
  .map((_, idx) => ({ id: idx, year: 2000 + idx }));

const mockSqlQuery = jest.spyOn(db, "sqlQuery");
const mockFindMany = jest.spyOn(db.season, "findMany");

describe("fetchSeasons", () => {
  const expectedYears = fakeSeasons.map(({ year }) => year);

  beforeAll(() => {
    const mockFindManyImplementation = (async () =>
      fakeSeasons) as typeof db.season.findMany;
    mockFindMany.mockImplementation(mockFindManyImplementation);
  });

  it("fetches seasons from the DB", async () => {
    const seasons = await fetchSeasons();
    expect(seasons).toEqual(expectedYears);
  });
});

describe("fetchPredictedRoundNumbers", () => {
  const season = 2020;

  describe("when round numbers are available", () => {
    const roundNumbers = Array(5)
      .fill(null)
      .map((_, idx) => ({
        roundNumber: idx + 1,
      }));

    beforeAll(() => {
      const mockSqlQueryImplementation = (async () =>
        roundNumbers) as typeof db.sqlQuery<Round[]>;
      mockSqlQuery.mockImplementation(mockSqlQueryImplementation);
    });

    it("fetches round numbers", async () => {
      const predictedRoundNumbers = await fetchPredictedRoundNumbers(season);
      expect(predictedRoundNumbers).toEqual(
        roundNumbers.map(({ roundNumber }) => roundNumber)
      );
    });
  });

  describe("when a round number is not available", () => {
    beforeAll(() => {
      const mockSqlQueryImplementation = (async () => []) as typeof db.sqlQuery<
        number[]
      >;
      mockSqlQuery.mockImplementation(mockSqlQueryImplementation);
    });

    it("is empty", async () => {
      const predictedRoundNumbers = await fetchPredictedRoundNumbers(season);
      expect(predictedRoundNumbers).toEqual([]);
    });
  });
});
