/* @flow */
/* eslint-disable */
// @generated
// This file was automatically generated and should not be edited.

// ====================================================
// GraphQL query operation: fetchYearlyPredictions
// ====================================================

export type fetchYearlyPredictions_fetchYearlyPredictions_predictionsByRound_modelMetrics = {
  __typename: "CumulativeMetricsByRoundType",
  modelName: string,
  /**
   * Cumulative mean of correct tips (i.e. accuracy) made by the given model for the given season.
   */
  cumulativeAccuracy: number,
  /**
   * Cumulative bits metric for the given season.
   */
  cumulativeBits: number,
  /**
   * Cumulative mean absolute error for the given season
   */
  cumulativeMeanAbsoluteError: number,
  /**
   * Cumulative sum of correct tips made by the given model for the given season
   */
  cumulativeCorrectCount: number,
  /**
   * Cumulative difference between predicted margin and actual margin for the given season.
   */
  cumulativeMarginDifference: number,
};

export type fetchYearlyPredictions_fetchYearlyPredictions_predictionsByRound = {
  __typename: "RoundType",
  roundNumber: number,
  /**
   * Cumulative performance metrics for predictions made by the given model through the given round
   */
  modelMetrics: Array<fetchYearlyPredictions_fetchYearlyPredictions_predictionsByRound_modelMetrics>,
};

export type fetchYearlyPredictions_fetchYearlyPredictions = {
  __typename: "SeasonType",
  seasonYear: number,
  /**
   * Match and prediction data grouped by round
   */
  predictionsByRound: Array<fetchYearlyPredictions_fetchYearlyPredictions_predictionsByRound>,
};

export type fetchYearlyPredictions = {
  fetchYearlyPredictions: fetchYearlyPredictions_fetchYearlyPredictions
};

export type fetchYearlyPredictionsVariables = {
  year?: ?number,
  roundNumber?: ?number,
  forCompetitionOnly?: ?boolean,
};/* @flow */
/* eslint-disable */
// @generated
// This file was automatically generated and should not be edited.

//==============================================================
// START Enums and Input Objects
//==============================================================

//==============================================================
// END Enums and Input Objects
//==============================================================