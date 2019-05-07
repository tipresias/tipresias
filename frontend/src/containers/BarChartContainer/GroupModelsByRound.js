// @flow
import type {
  Game,
} from '../../types';

const groupModelsByRound = (data: Array<Game>): any => {
  const modelsByRound = data.reduce((acc, currentItem) => {
    // eslint-disable-next-line camelcase
    const { mlModel: { name } } = currentItem;
    const { match: { roundNumber } } = currentItem;

    // round number key
    acc[roundNumber] = acc[roundNumber] || {};

    // model key
    acc[roundNumber][name] = acc[roundNumber][name] || {};

    // roundArray key
    acc[roundNumber][name].roundArray = acc[roundNumber][name].roundArray || [];
    acc[roundNumber][name].roundArray.push(currentItem);

    const roundPointTotal = acc[roundNumber][name].roundArray.reduce(
      (acc2, item) => acc2 + item.isCorrect, 0,
    );

    // total_points key
    acc[roundNumber][name].total_points = roundPointTotal || 0;

    return acc;
  }, {});

  return modelsByRound;
};

export default groupModelsByRound;
