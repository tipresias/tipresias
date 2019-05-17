// @flow
import type {
  CumulTipPointPerModel,
} from '../types';

const createCumulativeModels = (modelsByRound: any): Array<Array<CumulTipPointPerModel>> => {
  const roundsArray = Object.keys(modelsByRound);
  return roundsArray.map((currentRound, index) => {
    const modelKeyArray = Object.keys(modelsByRound[currentRound]);
    const cumulativeModels = modelKeyArray.map((model) => {
      const prevRound = parseInt(currentRound, 10) - 1;
      const currentModel = modelsByRound[currentRound][model];
      let prevModel;

      if (index === 0) {
        prevModel = { total_points: 0 };
      } else if (modelsByRound[prevRound][model] === undefined) {
        prevModel = modelsByRound[prevRound - 1][model];
      } else {
        prevModel = modelsByRound[prevRound][model];
      }
      const cumulativeTotalPoints = currentModel.total_points + prevModel.total_points;
      currentModel.total_points = cumulativeTotalPoints;
      return { model, cumulativeTotalPoints };
    });
    return cumulativeModels;
  });
};

export default createCumulativeModels;
