// @flow
import type { MatchesType, PredictionType } from '../../types';
import images from '../../images';

const { iconCheck, iconCross } = images;

type NewDataSet = Array<Array<string | Object>>;

// eslint-disable-next-line import/prefer-default-export
export const dataTransformer = (
  matches: MatchesType,
  principalModelName: string,
): NewDataSet => {
  const newDataSet = matches.reduce((acc, matchItem, currentIndex) => {
    if (matchItem.predictions.length === 0) return [];

    acc[currentIndex] = acc[currentIndex] || [];

    const [date] = matchItem.startDateTime.split('T');
    acc[currentIndex][0] = date;

    // predicted Winner (form principalModel)
    const [principleModelPrediction] = matchItem.predictions.filter((item: any) => item.mlModel.name === principalModelName);
    const { predictedWinner } = principleModelPrediction;
    acc[currentIndex][1] = predictedWinner.name;

    const marginForCompetition = matchItem.predictions.filter((item: any) => item.mlModel.forCompetition === true && item.predictedMargin !== null);
    // loop the array of predictions and choose the predictedmargin value that is higher
    const predictedMargin = marginForCompetition.reduce((prevValue: number, currentItem: PredictionType) => (currentItem.predictedMargin > prevValue ? currentItem.predictedMargin : prevValue), 0);
    acc[currentIndex][2] = predictedMargin.toString();

    // predictedWinProbability
    const winProbabilityForCompetition = matchItem.predictions.filter((item: any) => item.mlModel.forCompetition === true && item.predictedWinProbability !== null);
    const predictedWinProbability = winProbabilityForCompetition.reduce((prevValue: number, currentItem: PredictionType) => (currentItem.predictedWinProbability > prevValue ? currentItem.predictedWinProbability : prevValue), 0);
    // acc[currentIndex][3] = predictedWinProbability.toString();
    acc[currentIndex][3] = (Math.round(predictedWinProbability * 100) / 100).toString();

    // isCorrect (form principalModel)
    const { isCorrect } = principleModelPrediction;
    acc[currentIndex][4] = isCorrect ? { svg: true, text: 'correct', path: iconCheck } : { svg: true, text: 'incorrect', path: iconCross };
    return acc;
  }, []);
  return newDataSet;
};
