import React, { Component } from 'react';
import * as d3 from 'd3';

class BarChart extends Component {
  state = {
    bars: [],
    calculating: true,
  }

  componentDidMount() {
    const { data, year } = this.props;
    const height = 400;
    const width = 650;

    // 1. map to x position from round to screen pixels
    const xExtent = d3.extent(data, d => d.round_number);

    const xScale = d3.scaleLinear()
      .domain(xExtent)
      .range([0, width]);
    // get the ccumulative tip points
    // select data for selected year
    const filteredData = data.filter(item => item.year === year && item.model === 'oddsmakers');

    const ROUND_MIN = 1;
    const ROUND_MAX = 28;
    const cumulativeRounds = [];

    for (let i = ROUND_MIN; i <= ROUND_MAX; i += 1) {
      const filteredDataByRound = filteredData.filter(item => item.round_number === i);
      const total = filteredDataByRound.reduce((acc, item) => (acc + item.tip_point), 0);
      cumulativeRounds.push({ round_number: i, tip_point_total: total });
    }
    // sum all oddmaker ti_ppoints on the 2011
    // const tipPointTotal = filteredData.reduce((acc, item) => item.tip_point + acc, 0);
    console.log(cumulativeRounds);

    const yExtent = d3.extent(cumulativeRounds, d => d.tip_point_total);
    console.log(yExtent);

    const yScale = d3.scaleLinear()
      .domain(yExtent)
      .range([height, 0]);

    const colorScale = d3.scaleSequential(d3.interpolateSpectral)
      .domain(yExtent);


    const bars = cumulativeRounds.map(d => ({
      round: d.round_number,
      x: xScale(d.round_number),
      y: yScale(d.tip_point_total),
      height: yScale(0) - yScale(d.tip_point_total),
      width: 2,
      fill: colorScale(d.tip_point_total),
    }));

    this.setState({
      bars,
      calculating: false,
    });
  }

  render() {
    const { bars, calculating } = this.state;
    const { year } = this.props;

    return (
      <div>
        <p>
          BarChart for
          {year}
        </p>
        {
          !calculating && (
            <svg width="650" height="400" style={{ border: '1px solid black' }}>
              {
                bars.map(item => (
                  <rect
                    key={item.round}
                    x={item.x}
                    y={item.y}
                    width={item.width}
                    height={item.height}
                    fill={item.fill}
                  />
                ))
              }
            </svg>
          )

        }
      </div>
    );
  }
}
export default BarChart;
