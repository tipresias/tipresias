// @flow
import type {
  Game,
} from '../../../../types';

const groupModelsByRound = (data: Array<Game>): any => {
  const modelsByRound = data.reduce((acc, currentItem) => {
    // eslint-disable-next-line camelcase
    const { model, round_number } = currentItem;
    acc[round_number] = acc[round_number] || {};
    acc[round_number][model] = acc[round_number][model] || {};
    acc[round_number][model].round = acc[round_number][model].round || 0;
    acc[round_number][model].data = acc[round_number][model].data || [];
    acc[round_number][model].total_points = acc[round_number][model].total_points || [];
    acc[round_number][model].round = currentItem.round_number;

    acc[round_number][model].data.push(currentItem);

    const roundArray = acc[round_number][model].data;
    const roundPointTotal = roundArray.reduce((acc2, value) => acc2 + value.tip_point, 0);
    acc[round_number][model].total_points = roundPointTotal;

    return acc;
  }, {});
  return modelsByRound;
};

export default groupModelsByRound;
