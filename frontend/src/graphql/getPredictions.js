import { gql } from 'apollo-boost';

const GET_PREDICTIONS_QUERY = gql`
  query Predictions($year: Int){
    predictions(year: $year) {
      id
      match {
        startDateTime
        roundNumber
        year
        teammatchSet {
          atHome
          team {
            name
          }
          score
        }
      }
      mlModel {
        name
      }
      predictedWinner {
        name
      }
      predictedMargin
      isCorrect
    }
  }
`;
export default GET_PREDICTIONS_QUERY;
