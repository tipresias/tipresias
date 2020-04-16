/* eslint-disable camelcase */
// @flow
import type {
  fetchYearlyPredictions_fetchYearlyPredictions_predictionsByRound as predictionsByRoundType,
} from '../../graphql/graphql-types/fetchYearlyPredictions';

export type rowType = {
  modelName: string,
  [key: string]: number
}

// export type LineChartDataType = {
//   roundNumber: number,
//   modelMetrics: Array<rowType>
// }

type NewDataItem = {
  roundNumber: number,
  [key: string]: number
}
type NewDataSet = Array<NewDataItem>

const dataTransformerLineChart = (
  predictionsByRound: Array<predictionsByRoundType>,
  metric: Object,
): NewDataSet => {
  const newDataSet = predictionsByRound.reduce((acc, currentItem, currentIndex) => {
    const { roundNumber, modelMetrics } = currentItem;
    acc[currentIndex] = acc[currentIndex] || {};
    acc[currentIndex].roundNumber = roundNumber;
    modelMetrics.forEach((item) => {
      // TODO check the ? in modelMetrics type,
      const { modelName } = item;
      // cumulativeAccuracy: %
      if (metric.name === 'cumulativeAccuracy') {
        const metricPercentage = (item[metric.name] * 100);
        acc[currentIndex][modelName] = parseFloat(metricPercentage.toFixed(2));
      } else {
        // bits and MAE: decimal
        acc[currentIndex][modelName] = parseFloat(item[metric.name].toFixed(2));
      }
    });
    return acc;
  }, []);

  return newDataSet;
};

export default dataTransformerLineChart;
