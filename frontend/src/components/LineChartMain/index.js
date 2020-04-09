// @flow
import React from 'react';
import type { Node } from 'react';
import styled from 'styled-components/macro';
import {
  LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, Label,
} from 'recharts';
import { isEmpty } from 'lodash';
import type { LineChartDataType } from '../../types';

type PreviousDataSet = Array<LineChartDataType>;

type Props = {
  data: PreviousDataSet,
  models: Array<string>,
  metric: {name: string, label: string}
}

type NewDataItem = {
  roundNumber: number,
  [key: string]: number
}

type NewDataSet = Array<NewDataItem>

const dataTransformer = (previousDataSet: PreviousDataSet, metric: Object): NewDataSet => {
  const newDataSet = previousDataSet.reduce((acc, currentItem, currentIndex) => {
    const { roundNumber, modelMetrics } = currentItem;
    acc[currentIndex] = acc[currentIndex] || {};
    acc[currentIndex].roundNumber = roundNumber;
    modelMetrics.forEach((item) => {
      const { modelName } = item;
      // cumulativeAccuracy: %
      if (metric.name === 'cumulativeAccuracy') {
        const metricPercentage = (item[metric.name] * 100);
        acc[currentIndex][modelName] = parseFloat(metricPercentage.toFixed(2));
      } else {
        // bits and MAE: decimal
        acc[currentIndex][modelName] = parseFloat(item[metric.name].toFixed(2));
      }
    });
    return acc;
  }, []);
  return newDataSet;
};
export const LineChartMainStyled = styled.div`
  .recharts-label, .recharts-cartesian-axis-tick-value{
    tspan {
      fill: ${props => props.theme.colors.textColor};
    }
  }
`;

const getYLabel = label => (label === 'Accuracy' ? `${label} %` : label);

const LineChartMain = ({ data, models, metric }: Props): Node => {
  const dataTransformed = dataTransformer(data, metric);

  const colorblindFriendlyPalette = ['#E69F00', '#56B4E9', '#CC79A7', '#009E73', '#0072B2', '#D55E00', '#F0E442'];

  return (
    <LineChartMainStyled style={{ marginBottom: '2rem' }}>
      <ResponsiveContainer width="100%" height={451}>
        <LineChart
          width={800}
          height={800}
          data={dataTransformed}
          margin={{
            top: 5, right: 30, left: 20, bottom: 5,
          }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="roundNumber">
            <Label value="Rounds" offset={-10} position="insideBottom" />
          </XAxis>
          <YAxis label={{ value: getYLabel(metric.label), angle: -90, position: 'insideBottomLeft' }} />
          <Tooltip />
          <Legend wrapperStyle={{ bottom: -20, fontSize: '1.1rem' }} />
          {!isEmpty(models) && models.map((item, i) => (<Line dataKey={item} type="monotone" stroke={colorblindFriendlyPalette[i]} fill={colorblindFriendlyPalette[i]} key={`model-${item}`} />))}
        </LineChart>
      </ResponsiveContainer>
    </LineChartMainStyled>
  );
};

export default LineChartMain;
