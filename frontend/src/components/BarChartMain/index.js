// @flow
import React from 'react';
import type { Node } from 'react';
import {
  BarChart, Bar, CartesianGrid, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import type { BarChartDataType } from '../../types';

type PreviousDataSet = Array<BarChartDataType>;

type Props = {
  data: PreviousDataSet,
}

type NewDataItem = {
  roundNumber: number,
  [key: string]: number
}

type NewDataSet = Array<NewDataItem>

const dataTransformer = (previousDataSet: PreviousDataSet): NewDataSet => {
  const newDataSet = previousDataSet.reduce((acc, currentItem, currentIndex) => {
    acc[currentIndex] = acc[currentIndex] || {};
    acc[currentIndex].roundNumber = currentItem.roundNumber;
    currentItem.modelPredictions.forEach((item) => {
      const { modelName } = item;
      acc[currentIndex][modelName] = item.cumulativeCorrectCount;
    });
    return acc;
  }, []);
  return newDataSet;
};

const BarChartMain = ({ data }: Props): Node => {
  const dataTransformed = dataTransformer(data);
  return (
    <ResponsiveContainer width="100%" height={451}>
      <BarChart
        width={800}
        height={300}
        data={dataTransformed}
        margin={{
          top: 5, right: 30, left: 20, bottom: 5,
        }}
      >
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="roundNumber" />
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
