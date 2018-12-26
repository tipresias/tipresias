// @flow
import React from 'react';
import type { Node } from 'react';
import type { BarsDataType } from '../../../types';

type Props = {
  bars: Array<Array<BarsDataType>>
}
const BarChart = ({ bars }: Props): Node => (
  bars.map((item, index) => (
    // todo: add a key to bars array.
    // eslint-disable-next-line react/no-array-index-key
    <g transform="translate(20, 0)" key={index}>
      {
        item.map(i => (<rect
          key={i.key}
          x={i.x}
          y={i.y}
          width={i.width}
          height={i.height}
          fill={i.fill}
        />
        ))
      }
    </g>
  ))
);

export default BarChart;
