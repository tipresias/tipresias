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
  const modelsByRound = data.reduce((acc, currentItem) => {
    // The values to use as "keys" in the data structure
    const { mlModel: { name } } = currentItem;
    const { match: { roundNumber } } = currentItem;

    // creating the data structure:
    acc[roundNumber - 1] = acc[roundNumber - 1] || {};
    acc[roundNumber - 1][name] = acc[roundNumber - 1][name] || {};
    acc[roundNumber - 1][name].rounds = acc[roundNumber - 1][name].rounds || [];

    // pushing values to the data structure:
    acc[roundNumber - 1][name].rounds.push(currentItem);

    return acc;
  }, []);

  return modelsByRound;
};

export default groupModelsByRoundFlat;
