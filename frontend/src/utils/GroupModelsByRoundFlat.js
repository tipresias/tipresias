// @flow
import type {
  Game,
} from '../types';
/*
creating object like:

[
  {
    tipresias: {
      roundArray: []
    },
    another_model: {
      roundArray: []
    }
  }
]
*/

/*
[
  [{}, {}, {}, {}, {}]
]
*/

const groupModelsByRoundFlat = (data: Array<Game>): any => {
  const modelsByRound = data.reduce((final, currentItem) => {
    // eslint-disable-next-line camelcase
    const { mlModel: { name } } = currentItem;
    const { match: { roundNumber } } = currentItem;

    // creating the data structure:
    final[roundNumber - 1] = final[roundNumber - 1] || {};
    final[roundNumber - 1][name] = final[roundNumber - 1][name] || {};
    final[roundNumber - 1][name].rounds = final[roundNumber - 1][name].rounds || [];

    // pushing values to the data structure:
    final[roundNumber - 1][name].rounds.push(currentItem);

    return final;
  }, []);

  return modelsByRound;
};

export default groupModelsByRoundFlat;
