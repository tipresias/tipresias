import React, { Component } from 'react';
import * as d3 from 'd3';
import createChartObject from './drawChart';

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
    const { games, year } = this.props;
    this.calculateData(games, year);
  }

  componentDidUpdate(prevProps, prevState) {
    const { games, year } = this.props;
    if (year !== prevProps.year) {
      console.log('year, games', year, games);
      this.calculateData(games, year);
    }
  }

  calculateData(data, year) {
    const filteredDataByYear = data.filter(item => item.year === parseInt(year, 10));
    const { bars, xScale, yScale } = createChartObject(filteredDataByYear);
    this.setState({
      bars,
      calculating: false,
    }, () => {
      this.xAxis.scale(xScale);
      d3.select(this.xAxisRef.current).call(this.xAxis);
      this.yAxis.scale(yScale);
      d3.select(this.yAxisRef.current).call(this.yAxis);
    });
  }

  render() {
    const {
      bars,
      calculating,
    } = this.state;

    const { year } = this.props;
    const title = `BarChart for ${year}`;

    const xAxisTranslate = `translate(0, ${height - margin.bottom})`;
    const yAxisTranslate = `translate(${margin.left},0)`;
    return (
      <div>
        <div>
          {title}
        </div>
        {
          !calculating && (
            <svg viewBox="0 0 800 400" style={{ border: '1px solid black', height: 'auto', width: '80%' }}>
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
              <g ref={this.xAxisRef} transform={xAxisTranslate} />
              <g ref={this.yAxisRef} transform={yAxisTranslate} />
            </svg>)
        }
      </div>
    );
  }
}
export default BarChart;
