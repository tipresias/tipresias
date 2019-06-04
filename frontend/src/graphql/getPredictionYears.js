import { gql } from 'apollo-boost';

// eslint-disable-next-line import/prefer-default-export
export const GET_PREDICTION_YEARS_QUERY = gql`
  query PredictionYears{
    predictionYears
  }
`;
