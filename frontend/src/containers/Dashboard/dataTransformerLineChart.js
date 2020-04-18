// @flow
import type {
  fetchYearlyPredictions_fetchYearlyPredictions_predictionsByRound as RoundType,
} from '../../graphql/graphql-types/fetchYearlyPredictions';

export type rowType = {
  modelName: string,
  [key: string]: number
}

type NewDataItem = {
  roundNumber: number,
  [key: string]: number
}
type NewDataSet = Array<NewDataItem>

const dataTransformerLineChart = (
  predictionsByRound: Array<RoundType>,
  metric: Object,
): NewDataSet => {
  const newDataSet = predictionsByRound.reduce((acc, currentItem, currentIndex) => {
    const { roundNumber, modelMetrics } = currentItem;
    acc[currentIndex] = acc[currentIndex] || {};
    acc[currentIndex].roundNumber = roundNumber;
    modelMetrics.forEach((item) => {
      if (!item) return;
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
