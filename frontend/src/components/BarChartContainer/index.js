// @flow
import React from 'react';
import type { GameDataType, BarsDataType } from '../../types';
import {
  setGames,
  drawBars,
  createTipPointScale,
  createRoundScale,
} from './createChartObject';

import BarChart from './BarChart';
import Axis from './Axis';

type Props = {
  gamesByYear: Array<GameDataType>
}

type State = {
  bars: Array<Array<BarsDataType>>,
  xScale: Function,
  yScale: Function,
  isCalculating: boolean
}

const height = 400;
const width = 800;

class BarChartContainer extends React.Component<Props, State> {
    state = {
      bars: [],
      xScale: () => null,
      yScale: () => null,
      isCalculating: true,
    }

    componentDidMount() {
      const { gamesByYear } = this.props;
      this.setBars(gamesByYear);
    }

    componentDidUpdate(prevProps: { gamesByYear: Array<GameDataType> }) {
      const { gamesByYear } = this.props;
      if (gamesByYear !== prevProps.gamesByYear) {
        this.setBars(gamesByYear);
      }
    }

    setBars(gamesByYear: Array<GameDataType>) {
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
