/* eslint-disable camelcase */
// @flow

export type rowType = {
  modelName: string,
  [key: string]: number
}

export type LineChartDataType = {
  roundNumber: number,
  modelMetrics: Array<rowType>
}

type PreviousDataSet = Array<LineChartDataType>;

type NewDataItem = {
  roundNumber: number,
  [key: string]: number
}
type NewDataSet = Array<NewDataItem>

// eslint-disable-next-line import/prefer-default-export
export const dataTransformerLineChart = (
  previousDataSet: PreviousDataSet,
  metric: Object,
): NewDataSet => {
  const newDataSet = previousDataSet.reduce((acc, currentItem, currentIndex) => {
    const { roundNumber, modelMetrics } = currentItem;
    acc[currentIndex] = acc[currentIndex] || {};
    acc[currentIndex].roundNumber = roundNumber;
    modelMetrics.forEach((item) => {
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
