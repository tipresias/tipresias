// @flow
import type { MatchesType } from '../../types';

type NewDataSet = Array<Array<string>>;

// eslint-disable-next-line import/prefer-default-export
export const dataTransformer = (matches: MatchesType): NewDataSet => {
  const principalModelPrediction: any = matches[0].predictions.filter(prediction => (prediction.mlModel.isPrinciple === true));
  if (principalModelPrediction.length === 0) return [];


  const newDataSet = matches.reduce((acc, currentitem, currentIndex) => {
    if (currentitem.predictions.length === 0) return [];

    acc[currentIndex] = acc[currentIndex] || [];

    const homeTeamName = currentitem.homeTeam.name;
    const awayTeamName = currentitem.awayTeam.name;

    const [date] = currentitem.startDateTime.split('T');
    acc[currentIndex][0] = date;

    const predictionsForCompetition = currentitem.predictions.filter(prediction => prediction.mlModel.forCompetition === true);
    const principalModelName = principalModelPrediction.mlModel.name;

    // predicted Winner (form principalModel)
    const predictedWinner = principalModelPrediction.predictedWinner.name;
    acc[currentIndex][1] = predictedWinner;

    // predicted margin (form confidence_estimator)
    const getPredictedMargin = (predictions, principalName) => {
      const nonPrincipalModel: any = predictions.filter(item => item.mlModel.name !== principalName);
      return nonPrincipalModel.predictedMargin;
    };
    const predictedMargin = principalModelPrediction.predictedMargin || getPredictedMargin(predictionsForCompetition, principalModelName);
    acc[currentIndex][2] = predictedMargin;

    // predicted Loser (form principalModel)
    const getPredictedLoser = (predWinner, home, away) => ((predWinner === home) ? away : home);
    const predictedLoser = getPredictedLoser(predictedWinner, homeTeamName, awayTeamName);
    acc[currentIndex][3] = predictedLoser;

    // isCorrect (form principalModel)
    const { isCorrect } = principalModelPrediction;
    acc[currentIndex][4] = isCorrect ? 'yes' : 'no';


    return acc;
  }, []);
  return newDataSet;
};
