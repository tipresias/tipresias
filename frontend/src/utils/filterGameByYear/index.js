// @flow
import type { Game } from '../../types';

export default function filterGameByYear(
  gamesData: Array<Game>,
  year: number,
): Array<Game> {
  return gamesData.filter(
    item => item.year === parseInt(year, 10),
  );
}
