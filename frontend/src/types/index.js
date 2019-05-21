// @flow
export type NumericScale = (a: number) => number

export type StringScale = (a: string) => string

export type Game = {
  id: string,
  isCorrect: boolean,
  match: Object,
  mlModel: Object,
  predictedMargin: number,
  predictedWinner: Object
}

export type CumulTipPointPerModel = {
  cumulativeTotalPoints: number,
  model: string
}

export type createBarGroupsArgs = {
  barWidth: number,
  xScale: NumericScale,
  yScale: NumericScale,
  colorScale: StringScale,
  cumulativeModels: Array<Array<CumulTipPointPerModel>>
}

export type BarChartDataType = Array<Object>
