// @flow
import React from 'react';
import type { Node } from 'react';
import {
  LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, Label,
} from 'recharts';
import { isEmpty } from 'lodash';
import type { BarChartDataType } from '../../types';

type PreviousDataSet = Array<BarChartDataType>;

type Props = {
  data: PreviousDataSet,
  models: Array<string>,
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
      acc[currentIndex][modelName] = item.cumulativeAccuracy;
    });
    return acc;
  }, []);
  return newDataSet;
};

const LineChartMain = ({ data, models }: Props): Node => {
  const dataTransformed = dataTransformer(data);
  const colorblindFriendlyPalette = ['#E69F00', '#56B4E9', '#CC79A7', '#009E73', '#0072B2', '#D55E00', '#F0E442'];

  return (
    <ResponsiveContainer width="100%" height={451}>
      <LineChart
        width={800}
        height={300}
        data={dataTransformed}
        margin={{
          top: 5, right: 30, left: 20, bottom: 5,
        }}
      >
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="roundNumber">
          <Label value="Rounds" offset={0} position="insideBottom" />
        </XAxis>
        <YAxis label={{ value: 'Accuracy', angle: -90, position: 'insideLeft' }} />
        <Tooltip />
        <Legend />
        {!isEmpty(models) && models.map((item, i) => <Line dataKey={item} type="monotone" stroke={colorblindFriendlyPalette[i]} fill={colorblindFriendlyPalette[i]} key={`model-${item}`} />)}
      </LineChart>
    </ResponsiveContainer>
  );
};

export default LineChartMain;
