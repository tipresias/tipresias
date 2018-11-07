import React, { Component } from 'react';
import * as d3 from 'd3';
import createChartObject from './drawChart';
import BarChart from '../BarChart';

class BarChartContainer extends Component {
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
    return (
      <div>
        <div>
          {title}
        </div>
        {
          !calculating && (
            <BarChart
              bars={bars}
              xAxisRef={this.xAxisRef}
              yAxisRef={this.yAxisRef}
            />
          )
        }
      </div>
    );
  }
}
export default BarChartContainer;
