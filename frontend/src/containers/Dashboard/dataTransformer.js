// @flow
import type { MatchesType } from '../../types';

type NewDataSet = Array<Array<string>>;

// eslint-disable-next-line import/prefer-default-export
export const dataTransformer = (
  matches: MatchesType,
  principalModelName: string,
  secondaryModelName: string,
): NewDataSet => {
  const newDataSet = matches.reduce((acc, matchItem, currentIndex) => {
    if (matchItem.predictions.length === 0) return [];

    acc[currentIndex] = acc[currentIndex] || [];

    const homeTeamName = matchItem.homeTeam.name;
    const awayTeamName = matchItem.awayTeam.name;

    const [date] = matchItem.startDateTime.split('T');
    acc[currentIndex][0] = date;

    // predicted Winner (form principalModel)
    const [principleModelPrediction] = matchItem.predictions.filter((item: any) => item.mlModel.name === principalModelName);
    const { predictedWinner } = principleModelPrediction;
    acc[currentIndex][1] = predictedWinner.name;

    // TODO: clarify which was the default model for predictedMargin
    // predicted margin (form principalModel || confidence_estimator)
    const [secondaryModelPrediction] = matchItem.predictions.filter((item: any) => item.mlModel.name === secondaryModelName);
    const predictedMargin = principleModelPrediction.predictedMargin || secondaryModelPrediction.predictedMargin;
    acc[currentIndex][2] = predictedMargin.toString();

    // predicted Loser (form principalModel)
    const getPredictedLoser = (predWinner, home, away) => ((predWinner === home) ? away : home);
    const predictedLoser = getPredictedLoser(predictedWinner, homeTeamName, awayTeamName);
    acc[currentIndex][3] = predictedLoser;

    // isCorrect (form principalModel)
    const { isCorrect } = principleModelPrediction;
    acc[currentIndex][4] = isCorrect ? 'yes' : 'no';

    return acc;
  }, []);
  return newDataSet;
};
