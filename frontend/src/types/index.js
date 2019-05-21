// @flow
export type Game = {
  id: string,
  isCorrect: boolean,
  match: Object,
  mlModel: Object,
  predictedMargin: number,
  predictedWinner: Object
}

export type BarChartDataType = Array<Object>
