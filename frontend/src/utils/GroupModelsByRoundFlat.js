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
    // const { mlModel: { name } } = currentItem;
    const { match: { roundNumber } } = currentItem;

    // eslint-disable-next-line no-param-reassign
    final[roundNumber - 1] = final[roundNumber - 1] || [];
    final[roundNumber - 1].push(currentItem);

    return final;
  }, []);

  return modelsByRound;
};

export default groupModelsByRoundFlat;
