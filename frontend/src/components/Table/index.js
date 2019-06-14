// @flow
import React from 'react';
import type { Node } from 'react';

import type { LatestRoundPredictionsType, Row } from '../../types';


type PreviousDataSet = LatestRoundPredictionsType;
type NewDataSet = Array<Row>

type Props = {
  caption: string,
  headers: Array<string>,
  data: PreviousDataSet
}

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


const dataTransformer = (previousDataSet: PreviousDataSet): NewDataSet => {
  const newDataSet = previousDataSet.matches.reduce((acc, currentitem, currentIndex) => {
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


const Table = ({ caption, headers, data }: Props): Node => {
  const rows = dataTransformer(data);
  return (
    <table>
      {caption && <caption>{caption}</caption>}
      <tbody>
        <tr>
          {
            headers && headers.length > 0 && headers.map(item => (
              <th scope="col" key={item}>{item}</th>
            ))
          }
        </tr>
        {
          rows && rows.length > 0 && rows.map(row => (
            <tr key={Math.random()}>
              {row.map(value => (
                <td key={value}>{value}</td>
              ))}
            </tr>
          ))
        }
      </tbody>
    </table>
  );
};

export default Table;
