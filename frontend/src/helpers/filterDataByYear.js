// @flow
import type {
  GameDataType,
} from '../types';

const filterDataByYear = (
  gamesData: Array<GameDataType>,
  year: number,
): Array<GameDataType> => gamesData.filter(
  item => item.year === parseInt(year, 10),
);

export default filterDataByYear;
