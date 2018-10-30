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
    // year/round/model

    const { gamesByYear } = this.props;
    console.log(gamesByYear);


    const [xMin, xMax] = d3.extent(gamesByYear, d => d.round_number);

    const xScale = d3.scaleLinear()
      .domain([xMin, xMax + 1])
      .range([margin.left, width - margin.right]);


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

    // console.log(roundsArray);
    const data = roundsArray.map((currentRound, index) => {
      const modelKeyArray = Object.keys(modelsObject[currentRound]);
      // console.log(modelKeyArray);

      const dataModels = modelKeyArray.map((model) => {
        // console.log('currentRound >>', currentRound);
        // console.log('prev round >>', currentRound - 1);
        // console.log('modelsObject[currentRound][model] >> ', modelsObject[currentRound][model]);
        // console.log('modelsObject[currentRound - 1][model] >> ', index > 0 ? modelsObject[currentRound - 1][model] : {});

        const prevRound = currentRound - 1;
        const currentModel = modelsObject[currentRound][model];
        const prevModel = (index === 0 || modelsObject[prevRound][model] === undefined) ? { total_points: 0 } : modelsObject[prevRound][model];

        // console.log('currentModel', currentModel);
        // console.log('prevModel', prevModel);
        // console.log('currentModel', currentModel.total_points);
        // console.log('prevModel', prevModel.total_points);

        const cumulativeTotalPoints = currentModel.total_points + prevModel.total_points;
        currentModel.total_points = cumulativeTotalPoints;
        return cumulativeTotalPoints;
      });

      // console.log(dataModels);


      return { [currentRound]: dataModels };
    });
    // console.log(data);


    // const [min, max] = d3.extent(collection, d => d.cumulativeTipPoint);
    // const yScale = d3.scaleLinear()
    //   .domain([0, max])
    //   .range([height - margin.bottom, margin.top]);

    // const colorScale = d3.scaleOrdinal(d3.schemeCategory10);

    // for (let i = ROUND_MIN; i <= ROUND_MAX; i += 1) {
    //   // console.log(i);
    // }

    // const bars = collection.map((d) => {
    //   let x;

    //   if (d.model === 'oddsmakers') {
    //     x = xScale(d.round_number);
    //   }
    //   if (d.model === 'tipresias_betting') {
    //     x = xScale(d.round_number) + 10;
    //   }
    //   if (d.model === 'tipresias_match') {
    //     x = xScale(d.round_number) + 20;
    //   }

    //   const y = yScale(d.cumulativeTipPoint);
    //   const h = yScale(0) - yScale(d.cumulativeTipPoint);

    //   return ({
    //     key: `${d.model}-${d.round_number}`,
    //     round: d.round_number,
    //     x,
    //     y,
    //     height: h,
    //     width: 6,
    //     fill: colorScale(d.model),
    //   });
    // });


    // this.setState({
    //   bars,
    //   xScale,
    //   yScale,
    //   calculating: false,
    // });
  }

  componentDidUpdate() {
    // const { xScale, yScale } = this.state;
    // this.xAxis.scale(xScale);
    // d3.select(this.xAxisRef.current).call(this.xAxis);
    // this.yAxis.scale(yScale);
    // d3.select(this.yAxisRef.current).call(this.yAxis);
  }

  render() {
    return <div>WIP</div>;
    // const {
    //   bars,
    //   calculating,
    // } = this.state;
    // const { year } = this.props;

    // const xAxisTranslate = `translate(0, ${height - margin.bottom})`;
    // const yAxisTranslate = `translate(${margin.left},0)`;
    // return (
    //   <div>
    //     <p>
    //       BarChart for
    //       {year}
    //     </p>
    //     {
    //       !calculating && (
    //         <svg width="800" height="400" style={{ border: '1px solid black' }}>
    //           {
    //             bars.map(item => (<rect
    //               key={item.key}
    //               x={item.x}
    //               y={item.y}
    //               width={item.width}
    //               height={item.height}
    //               fill={item.fill}
    //               stroke={item.stroke}
    //               strokeWidth={item.strokeWidth}
    //             />
    //             ))
    //           }
    //           <g ref={this.xAxisRef} transform={xAxisTranslate} />
    //           <g ref={this.yAxisRef} transform={yAxisTranslate} />
    //         </svg>)
    //     }
    //   </div>
    // );
  }
}
export default BarChart;
