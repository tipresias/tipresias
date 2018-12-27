// @flow
import * as d3 from 'd3';
import type {
  GameDataType,
  createBarsFuncArgType,
  BarsDataType,
  CumulTipPointPerModelType,
} from '../../types';

let games;
let cumulTipPointPerModel;

const margin = {
  top: 20,
  right: 5,
  bottom: 20,
  left: 35,
};

export const setGames = (gamesArray: Array<GameDataType>): void => {
  games = gamesArray;
};

export const getGames = (): Array<GameDataType> => games;

const setCumulativeTipPointPerModel = (value: Array<Array<CumulTipPointPerModelType>>): void => {
  cumulTipPointPerModel = value;
};

const getCuTipPointPerModel = (): Array<Array<CumulTipPointPerModelType>> => cumulTipPointPerModel;

const prepareModel = () => {
  const data = getGames();
  const modelsObject = data.reduce((acc, currentItem) => {
    // todo: this will change when implementing graphql.
    // eslint-disable-next-line camelcase
    const { model, round_number } = currentItem;
    acc[round_number] = acc[round_number] || {};
    acc[round_number][model] = acc[round_number][model] || {};
    acc[round_number][model].round = acc[round_number][model].round || 0;
    acc[round_number][model].data = acc[round_number][model].data || [];
    acc[round_number][model].total_points = acc[round_number][model].total_points || [];
    acc[round_number][model].round = currentItem.round_number;

    acc[round_number][model].data.push(currentItem);

    const roundArray = acc[round_number][model].data;
    const roundPointTotal = roundArray.reduce((acc2, value) => acc2 + value.tip_point, 0);
    acc[round_number][model].total_points = roundPointTotal;

    return acc;
  }, {});
  return modelsObject;
};

const calculateCumulativeTotals = (modelsObject) => {
  const roundsArray = Object.keys(modelsObject);
  return roundsArray.map((currentRound, index) => {
    const modelKeyArray = Object.keys(modelsObject[currentRound]);
    const dataModels = modelKeyArray.map((model) => {
      const prevRound = parseInt(currentRound, 10) - 1;
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
};

export const createTipPointScale = () => {
  const height = 400;
  const lastItem = getCuTipPointPerModel().length - 1;
  const [, yMax] = d3.extent(
    getCuTipPointPerModel()[lastItem],
    item => item.cumulativeTotalPoints,
  );

  const tipPointScale = d3.scaleLinear()
    .domain([0, yMax])
    .range([height - margin.bottom, margin.top]);
  return tipPointScale;
};

export const createRoundScale = () => {
  const gamesByYear = getGames();
  const width = 800;
  const [xMin, xMax] = d3.extent(gamesByYear, d => d.round_number);
  const roundScale = d3.scaleLinear()
    .domain([xMin, xMax + 1])
    .range([margin.left, width - margin.right]);
  return roundScale;
};

const createModelColorScale = () => {
  const modelColorScale = d3.scaleOrdinal(d3.schemeCategory10);
  return modelColorScale;
};

const createBarsObject = ({
  barWidth,
  roundScale,
  tipPointScale,
  modelColorScale,
  cumulativeTipPointPerModel,
}: createBarsFuncArgType): Array<Array<BarsDataType>> => {
  const createCoordinates = ({ modelItem, modelItemIndex, roundItemIndex }) => {
    const x = roundScale(roundItemIndex) + (barWidth * modelItemIndex);
    const y = tipPointScale(modelItem.cumulativeTotalPoints);
    const h = tipPointScale(0) - tipPointScale(modelItem.cumulativeTotalPoints);
    return { x, y, h };
  };

  return cumulativeTipPointPerModel.map((roundItem, roundItemIndex) => {
    const barsPerRound = roundItem.map((modelItem, modelItemIndex) => {
      const { x, y, h } = createCoordinates({ modelItem, modelItemIndex, roundItemIndex });
      return ({
        key: `${roundItemIndex + 1}-${modelItem.model}`,
        round: roundItemIndex + 1,
        x: parseFloat(x),
        y,
        height: h,
        width: barWidth,
        fill: modelColorScale(modelItem.model),
      });
    });
    return barsPerRound;
  });
};

export const drawBars = (barWidth: number) => {
  const modelsObject = prepareModel();
  const cumulativeTipPointPerModel = calculateCumulativeTotals(modelsObject);

  setCumulativeTipPointPerModel(cumulativeTipPointPerModel);

  const roundScale = createRoundScale();

  const tipPointScale = createTipPointScale();

  const modelColorScale = createModelColorScale();

  const bars = createBarsObject({
    barWidth,
    roundScale,
    tipPointScale,
    modelColorScale,
    cumulativeTipPointPerModel,
  });
  return bars;
};
