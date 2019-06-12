import { gql } from 'apollo-boost';

// eslint-disable-next-line import/prefer-default-export
export const GET_YEARLY_PREDICTIONS_QUERY = gql`
  query YearlyPredictions($year: Int){
    yearlyPredictions(year: $year){
      predictionModelNames
       predictionsByRound{
        roundNumber
        modelPredictions{
          modelName
          cumulativeCorrectCount
        }
      }
   }
  }`;
