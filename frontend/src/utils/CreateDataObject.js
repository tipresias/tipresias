// @flow
import getRoundsByModels from './GetRoundsByModels';
import getRoundsTotalPoints from './GetRoundsTotalPoints';
import getRoundsTotalPointsCumulative from './GetRoundsTotalPointsCumulative';
import type {
  Game,
} from '../types';

const createDataObject = (data: Array<Game>): Array<Object> => {
  // TODO: use pipe here (output > input)
  const roundsByModels = getRoundsByModels(data);
  const roundsTotalPoints = getRoundsTotalPoints(roundsByModels);
  const roundsTotalPointsCumulative = getRoundsTotalPointsCumulative(roundsTotalPoints);
  return roundsTotalPointsCumulative;
};

export default createDataObject;
