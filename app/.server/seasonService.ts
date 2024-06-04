import * as R from "ramda";

import { season } from "./db";

export interface Season {
  id: number;
  year: number;
}

export const fetchSeasons = R.pipe(
  season.findMany,
  R.andThen(R.map(R.prop("year")))
);
