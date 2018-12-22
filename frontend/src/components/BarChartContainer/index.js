import React from 'react';
import {
  setGames,
  getGames,
  drawBars,
  createTipPointScale,
  createRoundScale,
} from './createChartObject';

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
    this.setBars(gamesByYear);
  }

  componentDidUpdate(prevProps, prevState) {
    const { gamesByYear } = this.props;
    if (gamesByYear !== prevProps.gamesByYear) {
      this.setBars(gamesByYear);
    }
  }

  setBars(gamesByYear) {
    setGames(gamesByYear);
    const bars = drawBars();

    const xScale = createRoundScale();
    const yScale = createTipPointScale();

    this.setState({
      bars,
      xScale,
      yScale,
      isCalculating: false,
    });
  }

  render() {
    const {
      bars,
      xScale,
      yScale,
      isCalculating,
    } = this.state;

    return (
      <div>
        wip
        {
          !isCalculating
          && (
            <svg viewBox={`0 0 ${width} ${height}`} style={{ height: 'auto', width: '100%' }}>
              <BarChart bars={bars} />
              <Axis xScale={xScale} yScale={yScale} />
            </svg>
          )
        }
      </div>
    );
  }
}
export default BarChartContainer;
