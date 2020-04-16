/* eslint-disable consistent-return */
/* eslint-disable camelcase */
// @flow
import images from '../../images';
import type {
  fetchLatestRoundPredictions_fetchLatestRoundPredictions_matches as MatchType,
  fetchLatestRoundPredictions_fetchLatestRoundPredictions_matches_predictions as PredictionType,
} from '../../graphql/graphql-types/fetchLatestRoundPredictions';
// import type { fetchLatestRoundPredictions_fetchLatestRoundPredictions_matches_predictions as PredictionType } from '../../graphql/graphql-types/fetchPredictions';

const { iconCheck, iconCross } = images;

export type ModelType = {
  name: string,
  forCompetition: boolean,
  isPrinciple: boolean
}

export type MatchesType = Array<MatchType>;

type NewDataSet = Array<Array<string | Object>>;

const getPredictedMargin = (
  predictionsWithMargin: Array<PredictionType> | null,
) => {
  if (!predictionsWithMargin) return [];
  return predictionsWithMargin.reduce(
    (prevValue: number, currentItem: PredictionType) => {
      if (!currentItem.predictedMargin) return 0;
      return (
        currentItem.predictedMargin > prevValue ? currentItem.predictedMargin : prevValue
      );
    }, 0,
  );
};

const dataTransformerTable = (
  matches: MatchesType,
  principalModelName: string,
): NewDataSet => {
  const newDataSet = matches.reduce((acc, matchItem, currentIndex) => {
    if (matchItem.predictions.length === 0) return [];

    acc[currentIndex] = acc[currentIndex] || [];

    const [date] = matchItem.startDateTime.split('T');
    acc[currentIndex][0] = date;

    // predicted Winner (form principalModel)
    const [predictionWithPrincipleModel] = matchItem.predictions.filter(
      (item: any) => (item && item.mlModel.name === principalModelName)
      ,
    );
    if (!predictionWithPrincipleModel) { return []; }
    acc[currentIndex][1] = predictionWithPrincipleModel.predictedWinner.name;

    const predictionsWithMargin = matchItem.predictions.filter(
      (item: any) => item.mlModel.forCompetition === true && item.predictedMargin !== null,
    );

    // loop the array of predictions and choose the predictedmargin value that is higher
    acc[currentIndex][2] = getPredictedMargin(predictionsWithMargin);

    // predictedWinProbability
    const winProbabilityForCompetition = matchItem.predictions.filter(
      (item: any) => item.mlModel.forCompetition === true && item.predictedWinProbability !== null,
    );

    const predictedWinProbability = winProbabilityForCompetition && winProbabilityForCompetition.reduce(
      (prevValue: number, currentItem: PredictionType) => {
        if (!currentItem.predictedWinProbability) return 0;
        return currentItem.predictedWinProbability > prevValue
          ? currentItem.predictedWinProbability
          : prevValue;
      },
      0,
    );
    acc[currentIndex][3] = `${(Math.round(predictedWinProbability * 100)).toString()}%`;

    // isCorrect (form principalModel)
    const { isCorrect } = principleModelPrediction;
    acc[currentIndex][4] = isCorrect
      ? { svg: true, text: 'prediction is correct', path: iconCheck }
      : { svg: true, text: 'prediction is incorrect', path: iconCross };
    return acc;
  }, []);
  return newDataSet;
};
export default dataTransformerTable;
