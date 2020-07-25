/* @flow */
/* eslint-disable */
// @generated
// This file was automatically generated and should not be edited.

// ====================================================
// GraphQL query operation: fetchSeasonPerformanceChartParameters
// ====================================================

export type fetchSeasonPerformanceChartParameters_fetchSeasonPerformanceChartParameters_availableMlModels = {
  __typename: "MLModelType",
  name: string,
  /**
   * Whether the model is the principal model for predicting match winners among all the models used in competitions (i.e. all competition models predict winners, but only one's predictions are official predicted winners of Tipresias).
   */
  isPrincipal: boolean,
  /**
   * Whether the model's predictions are used in any competitions.
   */
  usedInCompetitions: boolean,
};

export type fetchSeasonPerformanceChartParameters_fetchSeasonPerformanceChartParameters = {
  __typename: "SeasonPerformanceChartParametersType",
  /**
   * All season years for which model predictions exist in the database
   */
  availableSeasons: Array<number>,
  /**
   * All ML models that have predictions in the database.
   */
  availableMlModels: Array<fetchSeasonPerformanceChartParameters_fetchSeasonPerformanceChartParameters_availableMlModels>,
};

export type fetchSeasonPerformanceChartParameters = {
  /**
   * Parameters for displaying info and populating inputs for the season performance chart.
   */
  fetchSeasonPerformanceChartParameters: fetchSeasonPerformanceChartParameters_fetchSeasonPerformanceChartParameters
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