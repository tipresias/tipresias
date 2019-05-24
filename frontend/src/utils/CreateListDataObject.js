// @flow
import getRoundsByModels from './GetRoundsByModels';
import type {
  Game,
} from '../types';


const itemsMocked = [
  {
    match: 1,
    teams: [
      {
        name: 'team ABC', isHome: true, predictedMargin: 35,
      },
      {
        name: 'team DEF', isHome: false, predictedMargin: null,
      }],
  },
  {
    match: 2,
    teams: [
      {
        name: 'team GHI', isHome: false, predictedMargin: null,
      },
      {
        name: 'team JKL', isHome: true, predictedMargin: 10,
      }],
  },
  {
    match: 3,
    teams: [
      {
        name: 'team MNL', isHome: false, predictedMargin: 50,
      },
      {
        name: 'team OPQ', isHome: true, predictedMargin: null,
      }],
  },
  {
    match: 4,
    teams: [
      {
        name: 'team RST', isHome: true, predictedMargin: null,
      },
      {
        name: 'team UVW', isHome: false, predictedMargin: 12,
      }],
  },
];

const mockedCurrentRound = 6;

const createListDataObject = (data: Array<Game>): Array<Object> => {
  const roundsByModels = getRoundsByModels(data);
  const roundsByCurrentRoundTipresias = roundsByModels[mockedCurrentRound].tipresias.rounds.map(
    item => item,
  );

  // console.log(roundsByCurrentRoundTipresias);

  const newRoundsByCurrentRoundTipresias = roundsByCurrentRoundTipresias.reduce(
    (acc, currentitem, currentIndex) => {
      acc[currentIndex] = acc[currentIndex] || {};
      acc[currentIndex].match = currentIndex;
      acc[currentIndex].teams = acc[currentIndex].teams || [];

      currentitem.match.teammatchSet.forEach((element, i) => {
        console.log(element);

        const isWinner = (currentitem.predictedWinner.name === element.team[i].name);
        const team = {
          name: element.team[i].name,
          atHome: element.team[i].atHome,
          predictedMargin: (isWinner ? currentitem.predictedMargin : null),
        };

        acc[currentIndex].teams.push(team);
      });

      return acc;
    }, [],
  );

  console.log(newRoundsByCurrentRoundTipresias);

  return itemsMocked;
};

export default createListDataObject;
