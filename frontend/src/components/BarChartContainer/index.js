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
    const { gamesByYear } = this.props;
    this.calculateData(gamesByYear);
  }

  componentDidUpdate(prevProps, prevState) {
    const { gamesByYear } = this.props;
    if (gamesByYear !== prevProps.gamesByYear) {
      this.calculateData(gamesByYear);
    }
  }

  calculateData(gamesByYear) {
    const { bars, xScale, yScale } = createChartObject(gamesByYear);
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

    return (
      <div>
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
