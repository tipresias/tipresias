/**
 * @jest-environment node
 */

import { fetchSeasons } from "../../app/.server/seasonService";

const fakeSeasons = Array(5)
  .fill(null)
  .map((_, idx) => ({ id: idx, year: 2000 + idx }));

jest.mock<typeof import("../../app/.server/db")>("../../app/.server/db", () => {
  const originalDb = jest.requireActual<typeof import("../../app/.server/db")>(
    "../../app/.server/db"
  );

  return {
    ...originalDb,
    season: {
      ...originalDb.season,
      findMany: (async () => {
        return fakeSeasons;
      }) as typeof originalDb.season.findMany,
    },
  };
});

afterAll(() => {
  jest.restoreAllMocks();
});

describe("fetchSeasons", () => {
  const expectedYears = fakeSeasons.map(({ year }) => year);

  it("fetches seasons from the DB", async () => {
    const seasons = await fetchSeasons();
    expect(seasons).toEqual(expectedYears);
  });
});
