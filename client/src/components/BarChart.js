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
    // const filteredData = data.filter(item => item.year === year && item.model === 'oddsmakers');
    const filteredDataByYear = data.filter(item => item.year === year);
    // console.log(filteredDataByYear);


    const ROUND_MIN = 1;
    const ROUND_MAX = 28;
    const collection = [];
    const models = ['oddsmakers', 'tipresias_betting', 'tipresias_match'];
    /*
    [
      { round_number: 1, model: "oddsmakers", tip_point_total: total },
      { round_number: 1, model: "oddsmakers", tip_point_total: total },
      { round_number: 1, model: "oddsmakers", tip_point_total: total },
    ]
    */
    models.forEach((model) => {
      const filteredByModel = filteredDataByYear.filter(item => item.model === model);
      for (let i = ROUND_MIN; i <= ROUND_MAX; i += 1) {
        const filteredDataByRound = filteredByModel.filter(item => item.round_number === i);
        const total = filteredDataByRound.reduce((acc, item) => (acc + item.tip_point), 0);
        collection.push({
          model,
          round_number: i,
          tip_point_total: total,
        });
      }
    });
    // calculate cumulative values:
    // console.log(collection);
    const totals = models.map((model) => {
      const collectionFilteredByModel = collection.filter(item => item.model === model);
      const total = collectionFilteredByModel.reduce((acc, currentItem) => {
        const cumulativeTipPoint = currentItem.tip_point_total + acc;
        currentItem.cumulativeTipPoint = cumulativeTipPoint;
        return cumulativeTipPoint;
      }, 0);
      return total;
    });
    console.log(totals);

    const [min, max] = d3.extent(collection, d => d.cumulativeTipPoint);

    const yScale = d3.scaleLinear()
      .domain([0, max])
      .range([height, 0]);

    const colorScale = d3.scaleSequential(d3.interpolateSpectral)
      .domain([0, max]);

    const bars = collection.map((d) => {
      let strokeColor;
      if (d.model === 'oddsmakers') {
        strokeColor = 'red';
      }
      if (d.model === 'tipresias_betting') {
        strokeColor = 'blue';
      }
      if (d.model === 'tipresias_match') {
        strokeColor = 'yellow';
      }

      const y = yScale(d.cumulativeTipPoint);
      const h = yScale(0) - yScale(d.cumulativeTipPoint);

      return ({
        key: d.round_number + d.model,
        round: d.round_number,
        x: xScale(d.round_number),
        y,
        height: h,
        width: 10,
        fill: colorScale(d.cumulativeTipPoint),
        stroke: strokeColor,
        strokeWidth: 3,
      });
    });

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
                bars.map(item => (<rect
                  key={item.key}
                  x={item.x}
                  y={item.y}
                  width={item.width}
                  height={item.height}
                  fill={item.fill}
                  stroke={item.stroke}
                  strokeWidth={item.strokeWidth}
                />
                ))
              }
            </svg>)
        }
      </div>
    );
  }
}
export default BarChart;
