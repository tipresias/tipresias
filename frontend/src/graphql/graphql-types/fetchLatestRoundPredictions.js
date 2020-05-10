/* @flow */
/* eslint-disable */
// @generated
// This file was automatically generated and should not be edited.

// ====================================================
// GraphQL query operation: fetchLatestRoundPredictions
// ====================================================

export type fetchLatestRoundPredictions_fetchLatestRoundPredictions_matchPredictions = {
  __typename: "MatchPredictionType",
  startDateTime: any,
  predictedWinner: string,
  predictedMargin: number,
  predictedWinProbability: number,
  isCorrect: ?boolean,
};

export type fetchLatestRoundPredictions_fetchLatestRoundPredictions = {
  __typename: "RoundPredictionType",
  roundNumber: number,
  matchPredictions: Array<fetchLatestRoundPredictions_fetchLatestRoundPredictions_matchPredictions>,
};

export type fetchLatestRoundPredictions = {
  /**
   * Official Tipresias predictions for the latest round for which data is available
   */
  fetchLatestRoundPredictions: fetchLatestRoundPredictions_fetchLatestRoundPredictions
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