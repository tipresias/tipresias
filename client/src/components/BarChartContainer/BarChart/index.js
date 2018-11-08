import React from 'react';

const BarChart = ({ bars }) => (
  bars.map((item, index) => (
    <g key={index}>
      {
        item.map(i => (<rect
          key={i.key}
          x={i.x}
          y={i.y}
          width={i.width}
          height={i.height}
          fill={i.fill}
          stroke={i.stroke}
          strokeWidth={i.strokeWidth}
        />
        ))
      }
    </g>
  ))
);

export default BarChart;
