// @flow
import type { Game } from '../types';

const filterGameByYear = (
  gamesData: Array<Game>,
  year: number,
): Array<Game> => gamesData.filter(
  item => item.year === parseInt(year, 10),
);

export default filterGameByYear;
