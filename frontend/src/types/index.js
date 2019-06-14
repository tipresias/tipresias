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
  cumulativeCorrectCount: number
}

export type BarChartDataType = {
  roundNumber: number,
  modelPredictions: Array<BarDataType>
}

export type MatchType = {
  startDateTime: string,
  homeTeam: Object,
  awayTeam: Object,
  predictions: Array<Object>
}

export type LatestRoundPredictionsType = {
  roundNumber: number,
  matches: Array<MatchType>
};

export type Row = Array<string>;
