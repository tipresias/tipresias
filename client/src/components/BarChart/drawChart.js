import * as d3 from 'd3';

const prepareModel = (gamesByYear) => {
  const modelsObject = gamesByYear.reduce((acc, currentItem) => {
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
  return modelsObject;
};

const calculateCumulativeTotals = (modelsObject) => {
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
  return cumulativeTipPointPerModel;
};

const createScales = (cumulativeTipPointPerModel, gamesByYear) => {
  const height = 400;
  const width = 800;
  const margin = {
    top: 20,
    right: 5,
    bottom: 20,
    left: 35,
  };
  const [xMin, xMax] = d3.extent(gamesByYear, d => d.round_number);
  const xScale = d3.scaleLinear()
    .domain([xMin, xMax + 1])
    .range([margin.left, width - margin.right]);

  const [yMin, yMax] = d3.extent(cumulativeTipPointPerModel[27], item => item.cumulativeTotalPoints);
  const yScale = d3.scaleLinear()
    .domain([0, yMax])
    .range([height - margin.bottom, margin.top]);

  const colorScale = d3.scaleOrdinal(d3.schemeCategory10);
  return { xScale, yScale, colorScale };
};

const createBarsObject = (xScale, yScale, colorScale, cumulativeTipPointPerModel) => {
  const bars = cumulativeTipPointPerModel.map((roundItem, roundItemIndex) => {
    const barsPerRound = roundItem.map((modelItem) => {
      let x;

      if (modelItem.model === 'oddsmakers') {
        x = xScale(roundItemIndex);
      }
      if (modelItem.model === 'tipresias_betting') {
        x = xScale(roundItemIndex) + 6;
      }
      if (modelItem.model === 'tipresias_match') {
        x = xScale(roundItemIndex) + 12;
      }

      if (modelItem.model === 'tipresias_player') {
        x = xScale(roundItemIndex) + 18;
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
        fill: colorScale(modelItem.model)
      });
    });
    return barsPerRound;
  });
  return bars;
};

const createChartObject = (gamesByYear) => {
  console.log('gamesByYear >>>>>>>> ', gamesByYear);

  const modelsObject = prepareModel(gamesByYear);
  const cumulativeTipPointPerModel = calculateCumulativeTotals(modelsObject);
  const { xScale, yScale, colorScale } = createScales(cumulativeTipPointPerModel, gamesByYear);
  const bars = createBarsObject(xScale, yScale, colorScale, cumulativeTipPointPerModel);
  return { bars, xScale, yScale };
};

export default createChartObject;
