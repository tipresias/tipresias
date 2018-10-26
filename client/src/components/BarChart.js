import React, { Component } from 'react';
import * as d3 from 'd3';

const height = 400;
const width = 800;
const margin = {
  top: 20,
  right: 5,
  bottom: 20,
  left: 35,
};

class BarChart extends Component {
  state = {
    bars: [],
    calculating: true,
  }

  xAxisRef = React.createRef();

  yAxisRef = React.createRef();

  xAxis = d3.axisBottom().tickFormat(d => d);

  yAxis = d3.axisLeft().tickFormat(d => d);

  componentDidMount() {
    const { data, year } = this.props;

    // 1. map to x position from round to screen pixels
    const [xMin, xMax] = d3.extent(data, d => d.round_number);
    const xScale = d3.scaleLinear()
      .domain([xMin, xMax + 1])
      .range([margin.left, width - margin.right]);

    // get the ccumulative tip points
    // select data for selected year
    // const filteredData = data.filter(item => item.year === year && item.model === 'oddsmakers');
    const filteredDataByYear = data.filter(item => item.year === year);

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
      .range([height - margin.bottom, margin.top]);

    const colorScale = d3.scaleOrdinal(d3.schemeCategory10);

    for (let i = ROUND_MIN; i <= ROUND_MAX; i += 1) {
      console.log(i);
    }

    const bars = collection.map((d) => {
      let x;

      if (d.model === 'oddsmakers') {
        x = xScale(d.round_number);
      }
      if (d.model === 'tipresias_betting') {
        x = xScale(d.round_number) + 10;
      }
      if (d.model === 'tipresias_match') {
        x = xScale(d.round_number) + 20;
      }

      const y = yScale(d.cumulativeTipPoint);
      const h = yScale(0) - yScale(d.cumulativeTipPoint);

      return ({
        key: `${d.model}-${d.round_number}`,
        round: d.round_number,
        x,
        y,
        height: h,
        width: 6,
        fill: colorScale(d.model),
      });
    });

    this.setState({
      bars,
      xScale,
      yScale,
      calculating: false,
    });
  }

  componentDidUpdate() {
    const { xScale, yScale } = this.state;
    this.xAxis.scale(xScale);
    d3.select(this.xAxisRef.current).call(this.xAxis);
    this.yAxis.scale(yScale);
    d3.select(this.yAxisRef.current).call(this.yAxis);
  }

  render() {
    const {
      bars,
      calculating,
    } = this.state;

    const { year } = this.props;

    const xAxisTranslate = `translate(0, ${height - margin.bottom})`;
    const yAxisTranslate = `translate(${margin.left},0)`;
    return (
      <div>
        <p>
          BarChart for
          {year}
        </p>
        {
          !calculating && (
            <svg width="800" height="400" style={{ border: '1px solid black' }}>
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
              <g ref={this.xAxisRef} transform={xAxisTranslate} />
              <g ref={this.yAxisRef} transform={yAxisTranslate} />
            </svg>)
        }
      </div>
    );
  }
}
export default BarChart;
