// @flow
import groupModelsByRound from './GroupModelsByRound';
import createCumulativeModels from './CreateCumulativeModels';
import type {
  Game,
} from '../types';

const createDataObject = (data: Array<Game>): Array<Object> => {
  // Todo use pipe here (output > input)
  const modelsByRound = groupModelsByRound(data);
  const cumulativeModels = createCumulativeModels(modelsByRound);
  return cumulativeModels;
};

export default createDataObject;
