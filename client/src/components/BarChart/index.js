import React, { Component } from 'react';
import * as d3 from 'd3';
// import drawChart from 'drawChart.js';

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
    const { gamesByYear } = this.props;

    // prepare models objects
    const modelsObject = gamesByYear.reduce((acc, currentItem, currentIndex, arr) => {
      const { model, round_number } = currentItem;
      acc[round_number] = acc[round_number] || {};
      acc[round_number][model] = acc[round_number][model] || {};
      acc[round_number][model].round = acc[round_number][model].round || 0;
      acc[round_number][model].data = acc[round_number][model].data || [];
      acc[round_number][model].total_points = acc[round_number][model].total_points || [];
      acc[round_number][model].round = currentItem.round_number;

      acc[round_number][model].data.push(currentItem);

      const roundArray = acc[round_number][model].data;
      const roundPointTotal = roundArray.reduce((accumulator, currentVaue) => accumulator + currentVaue.tip_point, 0);
      acc[round_number][model].total_points = roundPointTotal;

      return acc;
    }, {});
    // console.log(modelsObject);

    const roundsArray = Object.keys(modelsObject);

    const cumulativeTipPointPerModel = roundsArray.map((currentRound, index) => {
      const modelKeyArray = Object.keys(modelsObject[currentRound]);
      const dataModels = modelKeyArray.map((model) => {
        const prevRound = currentRound - 1;
        const currentModel = modelsObject[currentRound][model];
        let prevModel;

        if (index === 0) {
          prevModel = { total_points: 0 };
        } else if (modelsObject[prevRound][model] === undefined) {
          prevModel = modelsObject[prevRound - 1][model];
        } else {
          prevModel = modelsObject[prevRound][model];
        }
        const cumulativeTotalPoints = currentModel.total_points + prevModel.total_points;
        currentModel.total_points = cumulativeTotalPoints;
        return { model, cumulativeTotalPoints };
      });
      return dataModels;
    });

    // console.log(cumulativeTipPointPerModel);

    const [xMin, xMax] = d3.extent(gamesByYear, d => d.round_number);
    const xScale = d3.scaleLinear()
      .domain([xMin, xMax + 1])
      .range([margin.left, width - margin.right]);


    const [yMin, yMax] = d3.extent(cumulativeTipPointPerModel[27], item => item.cumulativeTotalPoints);
    const yScale = d3.scaleLinear()
      .domain([0, yMax])
      .range([height - margin.bottom, margin.top]);

    const colorScale = d3.scaleOrdinal(d3.schemeCategory10);

    // console.log(cumulativeTipPointPerModel);

    const bars = cumulativeTipPointPerModel.map((roundItem, roundItemIndex) => {
      const barsPerRound = roundItem.map((modelItem) => {
        let x;

        if (modelItem.model === 'oddsmakers') {
          x = xScale(roundItemIndex);
        }
        if (modelItem.model === 'tipresias_betting') {
          x = xScale(roundItemIndex) + 10;
        }
        if (modelItem.model === 'tipresias_match') {
          x = xScale(roundItemIndex) + 20;
        }

        const y = yScale(modelItem.cumulativeTotalPoints);
        const h = yScale(0) - yScale(modelItem.cumulativeTotalPoints);

        return ({
          key: `${roundItemIndex + 1}-${modelItem.model}`,
          round: roundItemIndex + 1,
          x,
          y,
          height: h,
          width: 6,
          fill: colorScale(modelItem.model),
        });
      });
      return barsPerRound;
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
    console.log(bars);

    const { year } = this.props;
    const title = `BarChart for ${year}`;

    const xAxisTranslate = `translate(0, ${height - margin.bottom})`;
    const yAxisTranslate = `translate(${margin.left},0)`;
    return (
      <div>
        <p>
          {title}
        </p>
        {
          !calculating && (
            <svg width="800" height="400" style={{ border: '1px solid black' }}>
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
