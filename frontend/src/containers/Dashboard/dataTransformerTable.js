/* eslint-disable camelcase */
// @flow
import images from '../../images';
import type { fetchLatestRoundPredictions_fetchLatestRoundPredictions_matches } from '../../graphql/graphql-types/fetchLatestRoundPredictions';

const { iconCheck, iconCross } = images;

export type ModelType = {
  name: string,
  forCompetition: boolean,
  isPrinciple: boolean
}

// export type PredictionType = {
//   mlModel: ModelType,
//   predictedWinner: Object,
//   predictedMargin: number,
//   predictedWinProbability: number,
//   isCorrect: boolean,
// }

// export type MatchType = {
//   startDateTime: string,
//   homeTeam: Object,
//   awayTeam: Object,
//   predictions: Array<PredictionType>
// }

export type MatchesType = Array<fetchLatestRoundPredictions_fetchLatestRoundPredictions_matches>;

type NewDataSet = Array<Array<string | Object>>;

// eslint-disable-next-line import/prefer-default-export
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
    const [principleModelPrediction] = matchItem.predictions.filter(
      (item: any) => item.mlModel.name === principalModelName,
    );
    const { predictedWinner } = principleModelPrediction;
    acc[currentIndex][1] = predictedWinner.name;

    const marginForCompetition = matchItem.predictions.filter(
      (item: any) => item.mlModel.forCompetition === true && item.predictedMargin !== null,
    );
    // loop the array of predictions and choose the predictedmargin value that is higher
    const predictedMargin = marginForCompetition.reduce(
      (prevValue: number, currentItem: PredictionType) => (
        currentItem.predictedMargin > prevValue ? currentItem.predictedMargin : prevValue
      ), 0,
    );
    acc[currentIndex][2] = predictedMargin.toString();

    // predictedWinProbability
    const winProbabilityForCompetition = matchItem.predictions.filter(
      (item: any) => item.mlModel.forCompetition === true && item.predictedWinProbability !== null,
    );
    const predictedWinProbability = winProbabilityForCompetition.reduce(
      (prevValue: number, currentItem: PredictionType) => (
        currentItem.predictedWinProbability > prevValue
          ? currentItem.predictedWinProbability
          : prevValue
      ), 0,
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
