// @flow

import type {
  fetchSeasonModelMetrics_fetchSeasonModelMetrics_roundModelMetrics
  as RoundType,
} from '../../graphql/graphql-types/fetchSeasonModelMetrics';

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
  roundModelMetrics: Array<RoundType>,
  metric: Object,
): NewDataSet => {
  const newDataSet = roundModelMetrics.reduce((acc, currentItem, currentIndex) => {
    const { roundNumber, modelMetrics } = currentItem;
    acc[currentIndex] = acc[currentIndex] || {};
    acc[currentIndex].roundNumber = roundNumber;
    modelMetrics.forEach((item) => {
      if (!item) return;
      const { mlModel: { name } } = item;
      // cumulativeAccuracy: %
      if (metric.name === 'cumulativeAccuracy') {
        const metricPercentage = (item[metric.name] * 100);
        acc[currentIndex][name] = parseFloat(metricPercentage.toFixed(2));
      } else {
        // bits and MAE: decimal
        acc[currentIndex][name] = parseFloat(item[metric.name].toFixed(2));
      }
    });
    return acc;
  }, []);

  return newDataSet;
};

export default dataTransformerLineChart;
