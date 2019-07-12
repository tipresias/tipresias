/* @flow */
/* eslint-disable */
// This file was automatically generated and should not be edited.

// ====================================================
// GraphQL query operation: fetchYearlyPredictions
// ====================================================

export type fetchYearlyPredictions_fetchYearlyPredictions_predictionsByRound_modelPredictions = {
  __typename: "CumulativePredictionsByRoundType",
  modelName: ?string,
  /**
   * Cumulative sum of correct tips made by the given model for the given season
   */
  cumulativeCorrectCount: ?number,
};

export type fetchYearlyPredictions_fetchYearlyPredictions_predictionsByRound = {
  __typename: "RoundType",
  roundNumber: ?number,
  /**
   * Cumulative stats for predictions made by the given model through the given round
   */
  modelPredictions: ?Array<?fetchYearlyPredictions_fetchYearlyPredictions_predictionsByRound_modelPredictions>,
};

export type fetchYearlyPredictions_fetchYearlyPredictions = {
  __typename: "SeasonType",
  /**
   * All model names available for the given year
   */
  predictionModelNames: ?Array<?string>,
  /**
   * Match and prediction data grouped by round
   */
  predictionsByRound: ?Array<?fetchYearlyPredictions_fetchYearlyPredictions_predictionsByRound>,
};

export type fetchYearlyPredictions = {
  fetchYearlyPredictions: ?fetchYearlyPredictions_fetchYearlyPredictions
};

export type fetchYearlyPredictionsVariables = {
  year?: ?number
};/* @flow */
/* eslint-disable */
// This file was automatically generated and should not be edited.

//==============================================================
// START Enums and Input Objects
//==============================================================

//==============================================================
// END Enums and Input Objects
//==============================================================