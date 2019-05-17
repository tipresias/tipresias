import React from 'react';
import {
  BarChart, Bar, CartesianGrid, XAxis, YAxis, Tooltip, Legend,
} from 'recharts';
import groupModelsByRoundFlat from '../../utils/GroupModelsByRoundFlat';
// import createCumulativeModelsFlat from '../../utils/createCumulativeModelsFlat';


const createBarSet = (games) => {
  const modelsByRoundFlat = groupModelsByRoundFlat(games);
  console.log('modelsByRoundFlat >>>', modelsByRoundFlat);

  // const cumulativeModels = createCumulativeModelsFlat(modelsByRound);
  // console.log('cumulativeModelsFlat >>>', cumulativeModels);

  // add transformer here to get to data structure
  const newGames = [
    { round: '1', benchmark_estimator: 5, tipresias: 5 },
    { round: '2', benchmark_estimator: 13, tipresias: 13 },
    { round: '3', benchmark_estimator: 20, tipresias: 21 },
    { round: '4', benchmark_estimator: 32, tipresias: 35 },
    { round: '5', benchmark_estimator: 36, tipresias: 39 },
  ];
  return newGames;
};

const BarChartMain = ({ data }) => {
  const bars = createBarSet(data);
  return (
    <BarChart
      width={600}
      height={300}
      data={bars}
      margin={{
        top: 5, right: 30, left: 20, bottom: 5,
      }}
    >
      <CartesianGrid strokeDasharray="3 3" />
      <XAxis dataKey="round" />
      <YAxis />
      <Tooltip />
      <Legend />
      <Bar dataKey="tipresias" fill="#8884d8" />
      <Bar dataKey="benchmark_estimator" fill="#82ca9d" />
    </BarChart>
  );
};

export default BarChartMain;
