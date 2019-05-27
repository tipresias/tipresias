// @flow
import getRoundsByModels from './GetRoundsByModels';
import type {
  Game,
} from '../types';

const mockedCurrentRound = 6;

const createListDataObject = (data: Array<Game>): Array<Object> => {
  const roundsByModels = getRoundsByModels(data);
  const roundsByCurrentRoundTipresias = roundsByModels[mockedCurrentRound].tipresias.rounds.map(
    item => item,
  );

  const newRoundsByCurrentRoundTipresias = roundsByCurrentRoundTipresias.reduce(
    (acc, currentitem, currentIndex) => {
      acc[currentIndex] = acc[currentIndex] || {};
      acc[currentIndex].match = currentIndex;
      acc[currentIndex].teams = acc[currentIndex].teams || [];

      currentitem.match.teammatchSet.forEach((element) => {
        const isWinner = (currentitem.predictedWinner.name === element.team.name);

        const team = {
          name: element.team.name,
          atHome: element.atHome,
          predictedMargin: (isWinner ? currentitem.predictedMargin : null),
        };

        acc[currentIndex].teams.push(team);
      });

      return acc;
    }, [],
  );

  return newRoundsByCurrentRoundTipresias;
};

export default createListDataObject;
