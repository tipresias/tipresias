import React, { Component } from 'react';
import * as d3 from 'd3';

class BarChart extends Component {
  state = {
    bars: [], 
    calculating: true,
  }
  componentDidMount(){
    const {data} = this.props;
//1. map to x position from round to screen pixels
const xExtent = d3.extent(data, d => d.round_number)
    
const xScale = d3.scaleLinear()
  .domain(xExtent)
  .range([0, 650]);
  // get the ccumulative tip points 
  // select data for selected year
  const filteredData = data.filter((item) => { return item.year === 2010 });
  // sum all oddmaker ti_ppoints on the year 
  const tipPointTotal = filteredData.reduce((acc, item) => {
    return item.tip_point + acc;
  }, 0);

// const yExtent = d3.extent(data, d => d.tip_ )
  const yScale = d3.scaleLinear()
    .domain([0, tipPointTotal])
    .range([400, 0])
  
const bars =  filteredData.map(d => { 
  return {
    x: xScale(d.round_number),
    y: yScale(d.tip_point),
    height: 10,
    width: 2,
    fill: 'black'
  }
})
 console.log(bars)
this.setState({ 
  bars, 
  calculating: false
  })

}

  // static getDerivedStateFromProps(nextProps, prevState){
    // console.log("getDerivedStateFromProps")
    // const {data} = nextProps;
    // if (!data) return {};
  //   //1. map to x position from round to screen pixels
  //   const xExtent = d3.extent(data, d => d.round_number)
    
  //   const xScale = d3.scaleLinear()
  //     .domain(xExtent)
  //     .range([0, 650]);
  //     // get the ccumulative tip points 
  //     // select data for selected year
  //     const filteredData = data.filter((item) => { return item.year === 2010 });
  //     // sum all oddmaker ti_ppoints on the year 
  //     const tipPointTotal = filteredData.reduce((acc, item) => {
  //       return item.tip_point + acc;
  //     }, 0);

  //   // const yExtent = d3.extent(data, d => d.tip_ )
  //     const yScale = d3.scaleLinear()
  //       .domain([0, tipPointTotal])
  //       .range([400, 0])
      
  //   const bars =  filteredData.map(d => { 
  //     return {
  //       x: xScale(d.round_number),
  //       y: yScale(d.tip_point),
  //       height: 10,
  //       width: 2,
  //       fill: 'black'
  //     }
  //   })
  //  const newState = { 
  //   bars, 
  //   calculating: false
  //  }
   
    // return newState
  // }

  render(){
    const {bars} = this.state.bars;
    console.log(bars)
    return(
      <div>
     BarChart
     {
       this.state.calculating &&
     <svg width="650" height="400">
     {
       bars && bars.map(item => <rect 
         x={item.x}
         y={item.y}
         width={item.width}
         height={item.height}
         fill={item.fill}
         />)
     }
     </svg>
    }
      </div>
    )
  }
}
export default BarChart;