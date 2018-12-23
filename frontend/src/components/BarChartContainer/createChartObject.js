// @flow
import * as d3 from 'd3';
import type {
  GameDataType,
  createBarsFuncArgType,
  BarsDataType,
  CumulativeTipPointPerModelType,
} from '../../types';

let games;
let cumulativeTipPointPerModelArray;

const margin = {
  top: 20,
  right: 5,
  bottom: 20,
  left: 35,
};

export const setGames = (gamesArray: Array<GameDataType>) => {
  games = gamesArray;
};

export const getGames = (): Array<GameDataType> => {
  return games;
};

const setCumulativeTipPointPerModel = (value: Array<Array<CumulativeTipPointPerModelType>>) => {
  cumulativeTipPointPerModelArray = value;
};

const getCumulativeTipPointPerModel = (): Array<Array<CumulativeTipPointPerModelType>> => {
  return cumulativeTipPointPerModelArray;
};

const prepareModel = () => {
  const data = getGames();
  const modelsObject = data.reduce((acc, currentItem) => {
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
  const cumulativeTipPointPerModel = roundsArray.map((currentRound, index) => {
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
  return cumulativeTipPointPerModel;
};

export const createTipPointScale = () => {
  const cumulativeTipPointPerModel = getCumulativeTipPointPerModel();
  const height = 400;
  const [yMin, yMax] = d3.extent(
    cumulativeTipPointPerModel[cumulativeTipPointPerModel.length - 1],
    item => item.cumulativeTotalPoints
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
  roundScale,
  tipPointScale,
  modelColorScale,
  cumulativeTipPointPerModel,
}: createBarsFuncArgType): Array<Array<BarsDataType>> => {
  const bars = cumulativeTipPointPerModel.map((roundItem, roundItemIndex) => {
    const barsPerRound = roundItem.map((modelItem) => {
      let x;

      if (modelItem.model === 'oddsmakers') {
        x = roundScale(roundItemIndex);
      }
      if (modelItem.model === 'tipresias_all_data') {
        x = roundScale(roundItemIndex) + 5;
      }
      if (modelItem.model === 'tipresias_betting') {
        x = roundScale(roundItemIndex) + 10;
      }
      if (modelItem.model === 'tipresias_match') {
        x = roundScale(roundItemIndex) + 15;
      }

      if (modelItem.model === 'tipresias_player') {
        x = roundScale(roundItemIndex) + 20;
      }

      const y = tipPointScale(modelItem.cumulativeTotalPoints);


      const h = tipPointScale(0) - tipPointScale(modelItem.cumulativeTotalPoints);

      return ({
        key: `${roundItemIndex + 1}-${modelItem.model}`,
        round: roundItemIndex + 1,
        x: parseFloat(x),
        y,
        height: h,
        width: 5,
        fill: modelColorScale(modelItem.model),
      });
    });

    return barsPerRound;
  });
  return bars;
};

export const drawBars = () => {
  const modelsObject = prepareModel();
  const cumulativeTipPointPerModel = calculateCumulativeTotals(modelsObject);

  setCumulativeTipPointPerModel(cumulativeTipPointPerModel);

  const roundScale = createRoundScale();

  const tipPointScale = createTipPointScale();

  const modelColorScale = createModelColorScale();

  const bars = createBarsObject({
    roundScale,
    tipPointScale,
    modelColorScale,
    cumulativeTipPointPerModel,
  });
  return bars;
};
