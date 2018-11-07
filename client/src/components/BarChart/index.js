import React from 'react';

const height = 400;
const width = 800;
const margin = {
  top: 20,
  right: 5,
  bottom: 20,
  left: 35,
};
const xAxisTranslate = `translate(0, ${height - margin.bottom})`;
const yAxisTranslate = `translate(${margin.left},0)`;

const BarChart = ({
  bars,
  xAxisRef,
  yAxisRef,
}) => (
  <svg viewBox={`0 0 ${width} ${height}`} style={{ border: '1px solid black', height: 'auto', width: '80%' }}>
    {
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
    }
    <g ref={xAxisRef} transform={xAxisTranslate} />
    <g ref={yAxisRef} transform={yAxisTranslate} />
  </svg>
);


export default BarChart;
