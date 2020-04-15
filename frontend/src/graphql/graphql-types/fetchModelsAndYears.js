/* @flow */
/* eslint-disable */
// @generated
// This file was automatically generated and should not be edited.

// ====================================================
// GraphQL query operation: fetchModelsAndYears
// ====================================================

export type fetchModelsAndYears_fetchMlModels = {
  __typename: "MLModelType",
  name: string,
  /**
   * Whether the model is the principle model for predicting match winners among
   * all the models used in competitions (i.e. all competition models predict
   * winners, but only one's predictions are official predicted winners of Tipresias).
   */
  isPrinciple: ?boolean,
  /**
   * Whether the model's predictions are used in any competitions.
   */
  forCompetition: ?boolean,
};

export type fetchModelsAndYears_fetchYearlyPredictions_predictionsByRound_modelMetrics = {
  __typename: "CumulativeMetricsByRoundType",
  /**
   * Cumulative bits metric for the given season.
   */
  cumulativeBits: ?number,
  /**
   * Cumulative mean of correct tips (i.e. accuracy) made by the given model for the given season.
   */
  cumulativeAccuracy: ?number,
  /**
   * Cumulative mean absolute error for the given season
   */
  cumulativeMeanAbsoluteError: ?number,
};

export type fetchModelsAndYears_fetchYearlyPredictions_predictionsByRound = {
  __typename: "RoundType",
  roundNumber: ?number,
  /**
   * Cumulative performance metrics for predictions made by the given model through the given round
   */
  modelMetrics: ?Array<?fetchModelsAndYears_fetchYearlyPredictions_predictionsByRound_modelMetrics>,
};

export type fetchModelsAndYears_fetchYearlyPredictions = {
  __typename: "SeasonType",
  /**
   * Match and prediction data grouped by round
   */
  predictionsByRound: ?Array<?fetchModelsAndYears_fetchYearlyPredictions_predictionsByRound>,
};

export type fetchModelsAndYears = {
  /**
   * All years for which model predictions exist in the database
   */
  fetchPredictionYears: ?Array<?number>,
  fetchMlModels: ?Array<?fetchModelsAndYears_fetchMlModels>,
  fetchYearlyPredictions: ?fetchModelsAndYears_fetchYearlyPredictions,
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