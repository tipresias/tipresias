// @flow
import type {
  Game,
} from '../types';

const getRoundsByModels = (data: Array<Game>): Array<Object> => {
  const rounds = data.reduce((acc, currentItem) => {
    // The values to use as "keys" in the data structure
    const { mlModel: { name } } = currentItem;
    const { match: { roundNumber } } = currentItem;
    const index = roundNumber - 1;
    // creating the data structure:
    acc[index] = acc[index] || {};
    acc[index][name] = acc[index][name] || {};
    acc[index][name].rounds = acc[index][name].rounds || [];

    // pushing values to the data structure:
    acc[index][name].rounds.push(currentItem);

    // total_points key
    const totalPointsPerRound = acc[index][name].rounds.reduce(
      (totalPoints, currentMatch) => totalPoints + currentMatch.isCorrect, 0,
    );
    acc[index][name].total_points = totalPointsPerRound || 0;

    return acc;
  }, []);

  return rounds;
};

export default getRoundsByModels;
