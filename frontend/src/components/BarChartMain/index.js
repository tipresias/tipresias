import React from 'react';
import {
  BarChart, Bar, CartesianGrid, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import groupModelsByRoundFlat from '../../utils/GroupModelsByRoundFlat';
import createCumulativeModelsFlat from '../../utils/CreateCumulativeModelsFlat';


const createBarSet = (games) => {
  const modelsByRoundFlat = groupModelsByRoundFlat(games);
  const cumulativeModelsFlat = createCumulativeModelsFlat(modelsByRoundFlat);
  return cumulativeModelsFlat;
};

const BarChartMain = ({ data }) => {
  const bars = createBarSet(data);
  return (
    <ResponsiveContainer width="80%" height={300}>
      <BarChart
        width={800}
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
    </ResponsiveContainer>
  );
};

export default BarChartMain;
