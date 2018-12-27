// @flow
export type NumericScale = (a: number) => number

export type StringScale = (a: string) => string

export type GameDataType = {
  away_team: string,
  draw: number,
  home_margin: number,
  home_team: string,
  home_win: number,
  model: string,
  predicted_home_margin: number,
  predicted_home_win: number,
  round_number: number,
  tip_point: number,
  year: number
}

export type CumulTipPointPerModelType = {
  cumulativeTotalPoints: number,
  model: string
}

export type createBarsFuncArgType = {
  barWidth: number,
  roundScale: NumericScale,
  tipPointScale: NumericScale,
  modelColorScale: StringScale,
  cumulativeTipPointPerModel: Array<Array<CumulTipPointPerModelType>>
}

export type BarsDataType = {
  fill: string,
  height: number,
  key: string,
  round: number,
  width: number,
  x: number,
  y: number
}
