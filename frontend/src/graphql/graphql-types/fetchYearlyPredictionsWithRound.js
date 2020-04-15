/* @flow */
/* eslint-disable */
// @generated
// This file was automatically generated and should not be edited.

// ====================================================
// GraphQL query operation: fetchYearlyPredictionsWithRound
// ====================================================

export type fetchYearlyPredictionsWithRound_fetchYearlyPredictions_predictionsByRound_modelMetrics = {
  __typename: "CumulativeMetricsByRoundType",
  modelName: ?string,
  /**
   * Cumulative sum of correct tips made by the given model for the given season
   */
  cumulativeCorrectCount: ?number,
  /**
   * Cumulative bits metric for the given season.
   */
  cumulativeBits: ?number,
  /**
   * Cumulative mean absolute error for the given season
   */
  cumulativeMeanAbsoluteError: ?number,
  /**
   * Cumulative difference between predicted margin and actual margin for the given season.
   */
  cumulativeMarginDifference: ?number,
};

export type fetchYearlyPredictionsWithRound_fetchYearlyPredictions_predictionsByRound = {
  __typename: "RoundType",
  roundNumber: ?number,
  /**
   * Cumulative performance metrics for predictions made by the given model through the given round
   */
  modelMetrics: ?Array<?fetchYearlyPredictionsWithRound_fetchYearlyPredictions_predictionsByRound_modelMetrics>,
};

export type fetchYearlyPredictionsWithRound_fetchYearlyPredictions = {
  __typename: "SeasonType",
  seasonYear: ?number,
  /**
   * Match and prediction data grouped by round
   */
  predictionsByRound: ?Array<?fetchYearlyPredictionsWithRound_fetchYearlyPredictions_predictionsByRound>,
};

export type fetchYearlyPredictionsWithRound = {
  fetchYearlyPredictions: ?fetchYearlyPredictionsWithRound_fetchYearlyPredictions
};

export type fetchYearlyPredictionsWithRoundVariables = {
  year?: ?number,
  roundNumber?: ?number,
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