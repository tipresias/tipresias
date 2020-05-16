/* @flow */
/* eslint-disable */
// @generated
// This file was automatically generated and should not be edited.

// ====================================================
// GraphQL query operation: fetchPredictions
// ====================================================

export type fetchPredictions_fetchPredictions_match_teammatchSet_team = {
  __typename: "TeamType",
  name: string,
};

export type fetchPredictions_fetchPredictions_match_teammatchSet = {
  __typename: "TeamMatchType",
  atHome: boolean,
  team: fetchPredictions_fetchPredictions_match_teammatchSet_team,
  score: number,
};

export type fetchPredictions_fetchPredictions_match = {
  __typename: "MatchType",
  startDateTime: any,
  roundNumber: number,
  year: number,
  teammatchSet: Array<fetchPredictions_fetchPredictions_match_teammatchSet>,
};

export type fetchPredictions_fetchPredictions_mlModel = {
  __typename: "MLModelType",
  name: string,
};

export type fetchPredictions_fetchPredictions_predictedWinner = {
  __typename: "TeamType",
  name: string,
};

export type fetchPredictions_fetchPredictions = {
  __typename: "PredictionType",
  id: string,
  match: fetchPredictions_fetchPredictions_match,
  mlModel: fetchPredictions_fetchPredictions_mlModel,
  predictedWinner: fetchPredictions_fetchPredictions_predictedWinner,
  predictedMargin: ?number,
  isCorrect: ?boolean,
};

export type fetchPredictions = {
  fetchPredictions: Array<fetchPredictions_fetchPredictions>
};

export type fetchPredictionsVariables = {
  year?: ?number
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