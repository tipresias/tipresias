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
  isPrinciple: boolean,
  /**
   * Whether the model's predictions are used in any competitions.
   */
  forCompetition: boolean,
};

export type fetchModelsAndYears = {
  /**
   * All years for which model predictions exist in the database
   */
  fetchPredictionYears: Array<number>,
  fetchMlModels: Array<fetchModelsAndYears_fetchMlModels>,
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