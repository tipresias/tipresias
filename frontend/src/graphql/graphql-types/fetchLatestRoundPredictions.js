/* @flow */
/* eslint-disable */
// @generated
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
  /**
   * Whether the model's predictions are used in any competitions.
   */
  forCompetition: boolean,
  /**
   * Whether the model is the principle model for predicting match winners among
   * all the models used in competitions (i.e. all competition models predict
   * winners, but only one's predictions are official predicted winners of Tipresias).
   */
  isPrinciple: boolean,
};

export type fetchLatestRoundPredictions_fetchLatestRoundPredictions_matches_predictions_predictedWinner = {
  __typename: "TeamType",
  name: string,
};

export type fetchLatestRoundPredictions_fetchLatestRoundPredictions_matches_predictions = {
  __typename: "PredictionType",
  mlModel: fetchLatestRoundPredictions_fetchLatestRoundPredictions_matches_predictions_mlModel,
  predictedWinner: fetchLatestRoundPredictions_fetchLatestRoundPredictions_matches_predictions_predictedWinner,
  predictedMargin: ?number,
  predictedWinProbability: ?number,
  isCorrect: boolean,
};

export type fetchLatestRoundPredictions_fetchLatestRoundPredictions_matches = {
  __typename: "MatchType",
  year: number,
  startDateTime: any,
  homeTeam: ?fetchLatestRoundPredictions_fetchLatestRoundPredictions_matches_homeTeam,
  awayTeam: ?fetchLatestRoundPredictions_fetchLatestRoundPredictions_matches_awayTeam,
  predictions: Array<fetchLatestRoundPredictions_fetchLatestRoundPredictions_matches_predictions>,
};

export type fetchLatestRoundPredictions_fetchLatestRoundPredictions = {
  __typename: "RoundType",
  roundNumber: number,
  matches: Array<fetchLatestRoundPredictions_fetchLatestRoundPredictions_matches>,
};

export type fetchLatestRoundPredictions = {
  /**
   * Match info and predictions for the latest round for which data is available
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