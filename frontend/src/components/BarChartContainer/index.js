import React from 'react';
import createChartObject from './createChartObject';
import BarChart from './BarChart';
import Axis from './Axis';

const height = 400;
const width = 800;

class BarChartContainer extends React.Component {
  state = {
    bars: [],
    isCalculating: true,
  }

  componentDidMount() {
    const { games, year } = this.props;
    this.calculateData(games, year);
  }

  componentDidUpdate(prevProps, prevState) {
    const { games, year } = this.props;
    if (year !== prevProps.year) {
      this.calculateData(games, year);
    }
  }

  calculateData(data, year) {
    const filteredDataByYear = data.filter(item => item.year === parseInt(year, 10));
    const { bars, xScale, yScale } = createChartObject(filteredDataByYear);
    this.setState({
      bars,
      scales: { xScale, yScale },
      isCalculating: false,
    });
  }

  render() {
    const {
      bars,
      scales,
      isCalculating,
    } = this.state;

    const { year } = this.props;
    const title = `BarChart for ${year}`;
    return (
      <div>
        <div>
          {title}
        </div>
        {
          !isCalculating
          && (
            <svg viewBox={`0 0 ${width} ${height}`} style={{ height: 'auto', width: '100%' }}>
              <BarChart bars={bars} />
              <Axis scales={scales} />
            </svg>
          )
        }
      </div>
    );
  }
}
export default BarChartContainer;
