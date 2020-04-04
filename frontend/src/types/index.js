// @flow
export type Game = {
  id: string,
  isCorrect: boolean,
  match: Object,
  mlModel: Object,
  predictedMargin: number,
  predictedWinner: Object
}

export type BarDataType = {
  modelName: string,
  cumulativeAccuracy: number
}

export type LineChartDataType = {
  roundNumber: number,
  modelMetrics: Array<BarDataType>
}

export type ModelType = {
  name: string,
  forCompetition: boolean,
  isPrinciple: boolean
}

export type PredictionType = {
  mlModel: ModelType,
  predictedWinner: Object,
  predictedMargin: number,
  predictedWinProbability: number,
  isCorrect: boolean,
}

export type MatchType = {
  startDateTime: string,
  homeTeam: Object,
  awayTeam: Object,
  predictions: Array<PredictionType>
}

export type MatchesType = Array<MatchType>;
