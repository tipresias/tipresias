/* @flow */
/* eslint-disable */
// This file was automatically generated and should not be edited.

// ====================================================
// GraphQL query operation: fetchLatestRoundPredictions
// ====================================================

export type fetchLatestRoundPredictions_fetchLatestRoundPredictions_matches_homeTeam = {
  __typename: "TeamType",
  name: string,
};

export type fetchLatestRoundPredictions_fetchLatestRoundPredictions_matches_awayTeam = {
  __typename: "TeamType",
  name: string,
};

export type fetchLatestRoundPredictions_fetchLatestRoundPredictions_matches_predictions_mlModel = {
  __typename: "MLModelType",
  name: string,
};

export type fetchLatestRoundPredictions_fetchLatestRoundPredictions_matches_predictions_predictedWinner = {
  __typename: "TeamType",
  name: string,
};

export type fetchLatestRoundPredictions_fetchLatestRoundPredictions_matches_predictions = {
  __typename: "PredictionType",
  mlModel: fetchLatestRoundPredictions_fetchLatestRoundPredictions_matches_predictions_mlModel,
  predictedWinner: fetchLatestRoundPredictions_fetchLatestRoundPredictions_matches_predictions_predictedWinner,
  predictedMargin: number,
  isCorrect: boolean,
};

export type fetchLatestRoundPredictions_fetchLatestRoundPredictions_matches = {
  __typename: "MatchType",
  year: ?number,
  startDateTime: any,
  homeTeam: ?fetchLatestRoundPredictions_fetchLatestRoundPredictions_matches_homeTeam,
  awayTeam: ?fetchLatestRoundPredictions_fetchLatestRoundPredictions_matches_awayTeam,
  predictions: ?Array<?fetchLatestRoundPredictions_fetchLatestRoundPredictions_matches_predictions>,
};

export type fetchLatestRoundPredictions_fetchLatestRoundPredictions = {
  __typename: "RoundType",
  roundNumber: ?number,
  matches: ?Array<?fetchLatestRoundPredictions_fetchLatestRoundPredictions_matches>,
};

export type fetchLatestRoundPredictions = {
  /**
   * Match info and predictions for the latest round for which data is available
   */
  fetchLatestRoundPredictions: ?fetchLatestRoundPredictions_fetchLatestRoundPredictions
};/* @flow */
/* eslint-disable */
// This file was automatically generated and should not be edited.

//==============================================================
// START Enums and Input Objects
//==============================================================

//==============================================================
// END Enums and Input Objects
//==============================================================