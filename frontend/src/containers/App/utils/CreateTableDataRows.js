// @flow
import getRoundsByModels from './GetRoundsByModels';
import type {
  Game, Row,
} from '../../../types';

const MOCKED_CURRENT_ROUND_NUMBER = 6;

const createTableDataRows = (data: Array<Game>): Array<Row> => {
  const roundsByModels = getRoundsByModels(data);
  const matchsByCurrentRound = roundsByModels[MOCKED_CURRENT_ROUND_NUMBER].tipresias.rounds.map(
    item => item,
  );

  const newData = matchsByCurrentRound.reduce(
    (acc, currentitem, currentIndex) => {
      acc[currentIndex] = acc[currentIndex] || [];
      // date match item
      const [date] = currentitem.match.startDateTime.split('T');
      acc[currentIndex][0] = date;

      currentitem.match.teammatchSet.forEach((element) => {
        const isWinner = (currentitem.predictedWinner.name === element.team.name);
        if (isWinner) {
          // winner item
          acc[currentIndex][1] = element.team.name;
          // predictedMargin item
          acc[currentIndex][2] = (currentitem.predictedMargin).toString();
        } else {
          // loser item
          acc[currentIndex][3] = element.team.name;
        }
      });
      return acc;
    }, [],
  );

  return newData;
};

export default createTableDataRows;
