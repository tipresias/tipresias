import React from 'react';
import * as d3 from 'd3';

const height = 400;
const margin = {
  top: 20,
  right: 5,
  bottom: 20,
  left: 25,
};
const xAxisTranslate = `translate(0, ${height - margin.bottom})`;
const yAxisTranslate = `translate(${margin.left},0)`;

class Axis extends React.Component {
  xAxisRef = React.createRef();

  yAxisRef = React.createRef();

  xAxis = d3.axisBottom()
    .tickFormat(d => d);
  // xAxis = d3.axisBottom().tickValues([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28]);

  yAxis = d3.axisLeft().tickFormat(d => d);

  componentDidMount() {
    const { scales: { xScale, yScale } } = this.props;
    this.xAxis.scale(xScale);

    d3.select(this.xAxisRef.current).call(this.xAxis);
    this.yAxis.scale(yScale);
    d3.select(this.yAxisRef.current).call(this.yAxis);
  }

  render() {
    return (
      <g>
        <g ref={this.xAxisRef} transform={xAxisTranslate} style={{ border: '1px solid red' }} />
        <g ref={this.yAxisRef} transform={yAxisTranslate} style={{ border: '1px solid red' }} />
      </g>
    );
  }
}
export default Axis;
