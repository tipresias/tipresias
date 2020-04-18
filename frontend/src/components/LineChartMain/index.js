// @flow
import React from 'react';
import type { Node } from 'react';
import styled from 'styled-components/macro';
import {
  LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, Label,
} from 'recharts';
import { isEmpty } from 'lodash';


type Props = {
  data: Array<Object>,
  models: Array<string>,
  metric: {name: string, label: string}
}

export const LineChartMainStyled = styled.div`
  .recharts-label, .recharts-cartesian-axis-tick-value{
    tspan {
      fill: ${props => props.theme.colors.textColor};
    }
  }
`;

const getYLabel = label => (label === 'Accuracy' ? `${label} %` : label);

const LineChartMain = ({ data, models, metric }: Props): Node => {
  const colorblindFriendlyPalette = ['#E69F00', '#56B4E9', '#CC79A7', '#009E73', '#0072B2', '#D55E00', '#F0E442'];

  return (
    <LineChartMainStyled style={{ marginBottom: '2rem' }}>
      <ResponsiveContainer width="100%" height={451}>
        <LineChart
          width={800}
          height={800}
          data={data}
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
