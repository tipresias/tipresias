/* @flow */
/* eslint-disable */
// @generated
// This file was automatically generated and should not be edited.

// ====================================================
// GraphQL query operation: fetchSeasonModelMetrics
// ====================================================

export type fetchSeasonModelMetrics_fetchSeasonModelMetrics_roundModelMetrics_modelMetrics_mlModel = {
  __typename: "MLModelType",
  name: string,
};

export type fetchSeasonModelMetrics_fetchSeasonModelMetrics_roundModelMetrics_modelMetrics = {
  __typename: "ModelMetricsByRoundType",
  mlModel: fetchSeasonModelMetrics_fetchSeasonModelMetrics_roundModelMetrics_modelMetrics_mlModel,
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

export type fetchSeasonModelMetrics_fetchSeasonModelMetrics_roundModelMetrics = {
  __typename: "RoundType",
  roundNumber: number,
  /**
   * Performance metrics for predictions made by the given model through the given round
   */
  modelMetrics: Array<fetchSeasonModelMetrics_fetchSeasonModelMetrics_roundModelMetrics_modelMetrics>,
};

export type fetchSeasonModelMetrics_fetchSeasonModelMetrics = {
  __typename: "SeasonType",
  season: number,
  /**
   * Model performance metrics grouped by round
   */
  roundModelMetrics: Array<fetchSeasonModelMetrics_fetchSeasonModelMetrics_roundModelMetrics>,
};

export type fetchSeasonModelMetrics = {
  fetchSeasonModelMetrics: fetchSeasonModelMetrics_fetchSeasonModelMetrics
};

export type fetchSeasonModelMetricsVariables = {
  season?: ?number,
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