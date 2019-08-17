// @flow
import type { MatchesType } from '../../types';

type NewDataSet = Array<Array<string>>;


// eslint-disable-next-line import/prefer-default-export
export const dataTransformer = (previousDataSet: MatchesType): NewDataSet => {
  const newDataSet = previousDataSet.reduce((acc, currentitem, currentIndex) => {
    if (currentitem.predictions.length === 0) throw new Error();

    acc[currentIndex] = acc[currentIndex] || [];

    const homeTeam = currentitem.homeTeam.name;
    const awayTeam = currentitem.awayTeam.name;

    const [date] = currentitem.startDateTime.split('T');
    acc[currentIndex][0] = date;

    const predictedWinner = currentitem.predictions[0].predictedWinner.name;
    acc[currentIndex][1] = predictedWinner;

    const { predictedMargin } = currentitem.predictions[0];
    acc[currentIndex][2] = predictedMargin;

    const getPredictedLoser = (predWinner, home, away) => ((predWinner === home) ? away : home);
    const predictedLoser = getPredictedLoser(predictedWinner, homeTeam, awayTeam);
    acc[currentIndex][3] = predictedLoser;

    const { isCorrect } = currentitem.predictions[0];
    acc[currentIndex][4] = isCorrect ? 'yes' : 'no';

    return acc;
  }, []);
  return newDataSet;
};


// input: previousDataSet.matches =
// [{
//   "startDateTime": "2018-09-28T13:00:00+00:00",
//   "homeTeam": { "name": "West Coast", "__typename": "TeamType" },
//   "awayTeam": { "name": "Collingwood", "__typename": "TeamType" },
//   "predictions": [
//     {
//       "mlModel": { "name": "tipresias", "__typename": "MLModelType" },
//       "predictedWinner": { "name": "West Coast", "__typename": "TeamType" },
//       "predictedMargin": 16,
//       "isCorrect": true, "__typename": "PredictionType"
//     }
//    ],
// }]

// output:  rows =
// [
//  ['Date', 'Predicted Winner', 'Predicted margin', 'Predicted Loser', 'is Correct?']
// ]
