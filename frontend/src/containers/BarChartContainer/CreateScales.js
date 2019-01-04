// @flow
import * as d3 from 'd3';
import type {
  CumulTipPointPerModel,
} from '../../../../types';

const margin = {
  top: 20,
  right: 5,
  bottom: 20,
  left: 35,
};

export const createTipPointScale = (
  cumulativeModels: Array<Array<CumulTipPointPerModel>>,
  height: number,
) => {
  const lastItem = cumulativeModels.length - 1;
  const [, maxValue] = d3.extent(
    cumulativeModels[lastItem],
    item => item.cumulativeTotalPoints,
  );

  const tipPointScale = d3.scaleLinear()
    .domain([0, maxValue])
    .range([height - margin.bottom, margin.top]);
  return tipPointScale;
};

export const createRoundScale = (
  cumulativeModels: Array<Array<CumulTipPointPerModel>>,
  width: number,
) => {
  const minValue = 1;
  const maxValue = cumulativeModels.length;
  const roundScale = d3.scaleLinear()
    .domain([minValue, maxValue])
    .range([margin.left, width - margin.right]);
  return roundScale;
};

export const createColorScale = () => {
  const modelColorScale = d3.scaleOrdinal(d3.schemeCategory10);
  return modelColorScale;
};
