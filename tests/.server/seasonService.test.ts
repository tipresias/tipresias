/**
 * @jest-environment node
 */

import {
  Round,
  fetchLatestPredictedRound,
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

describe("fetchLatestPredictedRound", () => {
  const season = 2020;

  describe("when a round number is available", () => {
    const roundNumber = 5;

    beforeAll(() => {
      const mockSqlQueryImplementation = (async () => [
        { number: roundNumber },
      ]) as typeof db.sqlQuery<Round[]>;
      mockSqlQuery.mockImplementation(mockSqlQueryImplementation);
    });

    it("fetches a round number", async () => {
      const latestPredictedRound = await fetchLatestPredictedRound(season);
      expect(latestPredictedRound).toEqual(roundNumber);
    });
  });

  describe("when a round number is not available", () => {
    beforeAll(() => {
      const mockSqlQueryImplementation = (async () => []) as typeof db.sqlQuery<
        number[]
      >;
      mockSqlQuery.mockImplementation(mockSqlQueryImplementation);
    });

    it("fetches a round number", async () => {
      const latestPredictedRound = await fetchLatestPredictedRound(season);
      expect(latestPredictedRound).toBeNull();
    });
  });
});
