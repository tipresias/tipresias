/* @flow */
/* eslint-disable */
// @generated
// This file was automatically generated and should not be edited.

// ====================================================
// GraphQL query operation: fetchLatestRoundMetrics
// ====================================================

export type fetchLatestRoundMetrics_fetchLatestRoundMetrics = {
  __typename: "RoundMetricsType",
  season: number,
  roundNumber: number,
  /**
   * Cumulative bits metric for the given season.
   */
  cumulativeBits: number,
  /**
   * Cumulative mean absolute error for the given season
   */
  cumulativeMeanAbsoluteError: number,
  /**
   * Cumulative sum of correct tips for the given season
   */
  cumulativeCorrectCount: number,
  /**
   * Cumulative difference between predicted margin and actual margin for the given season.
   */
  cumulativeMarginDifference: number,
};

export type fetchLatestRoundMetrics = {
  /**
   * Performance metrics for Tipresias models for the current season through the last-played round.
   */
  fetchLatestRoundMetrics: fetchLatestRoundMetrics_fetchLatestRoundMetrics
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